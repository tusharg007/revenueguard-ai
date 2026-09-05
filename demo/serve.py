"""Demo-only routes around the unchanged FastAPI application.

Bind exclusively to localhost. All state lives in demo/work and dedicated Redis.
No scores, actions, approvals or success results are fabricated.
"""
import asyncio
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from backend.api.main import app
from backend.config import get_settings
from backend.db import database
from backend.db.orm_models import RecoveryCase
from backend.experiments.assignment import assign_experiment_arm
from backend.gateway_health.aggregator import GatewayHealthAggregator
from backend.worker import process_case

assert 'demo/work/' in get_settings().DATABASE_URL.replace('\\', '/')
assert get_settings().REDIS_URL == 'redis://127.0.0.1:6389/0'

def chosen_id(prefix):
    for i in range(1000):
        name = f'REC-{prefix}-{i:03}'
        if assign_experiment_arm(name).value == 'treatment':
            return name
    raise RuntimeError('No treatment bucket')

@app.post('/demo/seed-health')
async def seed_health():
    r = app.state.redis
    if r is None:
        raise HTTPException(503, 'Dedicated Redis unavailable')
    a = GatewayHealthAggregator(r)
    for bank in ['SBI', 'HDFC', 'ICICI']:
        for i in range(80):
            await a.record_outcome(bank, 'upi', 'success' if i < 76 else 'timeout')
    return {'seeded': True, 'source': 'synthetic local telemetry'}

@app.post('/demo/scenarios')
async def scenarios():
    ids = {'hero': chosen_id('SBI-RECOVERY'), 'approval': chosen_id('HIGH-VALUE')}
    for key, amount in [('hero', 890000), ('approval', 7500000)]:
        cid = ids[key]
        async with database.async_session_maker() as s:
            existing = await s.scalar(select(RecoveryCase).where(RecoveryCase.case_id == cid))
            if existing:
                continue
            s.add(RecoveryCase(
                case_id=cid, event_type='payment_failed', external_payment_id='pay_demo_'+key,
                amount_paise=amount, failure_category='systemic', failure_source='bank',
                failure_reason='payment_failed', error_code='GATEWAY_ERROR',
                customer_id='synthetic_customer_'+key, merchant_id='demo_merchant',
                created_at=datetime.now(timezone.utc),
                customer_data={'name':'Demo customer','email':'','phone':'',
                    'opted_out':False, 'total_transactions':120,'failed_transactions':2,
                    'lifetime_value_paise':25000000,'preferred_language':'en',
                    '_revenueguard_context':{'metadata':{'bank_name':'SBI','payment_method':'upi'},
                      'error_description':'Bank authorization temporarily unavailable; systemic SBI UPI outage.'}}
            ))
            await s.commit()
        await process_case(cid, app.state.redis)
    return ids

@app.get('/demo/claims')
def claims():
    return json.loads(Path('evals/results/summary.json').read_text(encoding='utf-8'))
