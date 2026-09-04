# RevenueGuard AI — Codex Execution Prompts

> [!TIP]
> **Codex Model Guide** (Plus subscription):
> - **GPT-5.5** + Medium thinking → Simple structured code (config, models, data gen)
> - **GPT-5.6 Terra** + Medium thinking → Standard backend work (API, worker, frontend)
> - **GPT-5.6 Sol** + High thinking → Complex reasoning tasks (ML training, LangGraph agents, evaluation)
>
> **Execute in order.** Each prompt produces a testable unit. Run the checkpoint after each before proceeding.

---

## Prompt 1: Foundation — Config, Models, Database

**Model**: GPT-5.5 | **Thinking**: Medium

```
You are building RevenueGuard AI, an intelligent payment recovery system for Indian merchants using Razorpay. The project is at the root of this repo.

Create the following files. The project uses Python 3.11, FastAPI, SQLAlchemy async, and Pydantic v2.

## File 1: backend/__init__.py
Empty file.

## File 2: backend/config.py
Pydantic Settings class using pydantic-settings that loads from .env file:
- GROQ_API_KEY: str = ""
- OPENROUTER_API_KEY: str = ""
- LLM_PROVIDER: str = "groq"  # "groq" or "openrouter"
- LLM_MODEL: str = "llama-3.3-70b-versatile"
- RAZORPAY_KEY_ID: str
- RAZORPAY_KEY_SECRET: str
- RAZORPAY_WEBHOOK_SECRET: str = ""
- DATABASE_URL: str = "sqlite+aiosqlite:///./revenueguard.db"
- REDIS_URL: str = "redis://localhost:6379"
- HIGH_VALUE_THRESHOLD: int = 5000000  # ₹50K in paise
- MAX_RETRY_ATTEMPTS: int = 3
- COOLDOWN_HOURS: int = 24
- QUIET_HOURS_START: int = 21  # 9 PM IST
- QUIET_HOURS_END: int = 9    # 9 AM IST
- EXPERIMENT_VARIANT_PCT: int = 20
- N8N_APPROVAL_WEBHOOK_URL: str = ""
- APP_ENV: str = "development"

Use @lru_cache for singleton. Use model_config with env_file=".env".

## File 3: backend/models/__init__.py
Empty.

## File 4: backend/models/enums.py
Python enums (str, Enum):
- EventType: PAYMENT_FAILED, SUBSCRIPTION_HALTED, SUBSCRIPTION_PENDING, CHECKOUT_ABANDONED, INVOICE_EXPIRED, INVOICE_OVERDUE
- EventStatus: DETECTED, TRIAGING, DIAGNOSING, STRATEGIZING, EXECUTING, RECOVERED, FAILED, ESCALATED, STOPPED
- FailureCategory: CUSTOMER, SYSTEMIC, BUSINESS, UNKNOWN
- FailureSource: CUSTOMER, BANK, GATEWAY, NETWORK, BUSINESS, RAZORPAY, UNKNOWN
- ActionType: SMART_RETRY, PAYMENT_LINK, NUDGE_EMAIL, NUDGE_SMS, NUDGE_WHATSAPP, ESCALATE_HUMAN, DEFER, STOP
- RecoveryChannel: SMS, EMAIL, WHATSAPP, IN_APP
- Priority: CRITICAL, HIGH, MEDIUM, LOW
- GatewayHealthState: CLOSED, OPEN, HALF_OPEN  (circuit breaker — CLOSED means healthy)
- ExperimentArm: CONTROL, TREATMENT

## File 5: backend/models/schemas.py
Pydantic v2 BaseModel classes:

CustomerProfile:
  customer_id: str
  name: str
  email: str
  phone: str
  upi_id: str | None = None
  preferred_language: str = "en"  # en/hi/hinglish
  lifetime_value_paise: int = 0
  total_transactions: int = 0
  failed_transactions: int = 0
  last_payment_date: datetime | None = None
  opted_out: bool = False

NormalizedFailureEvent:
  case_id: str  # UUID
  event_type: EventType
  processor: str = "razorpay"
  external_payment_id: str
  external_order_id: str | None = None
  amount_paise: int
  currency: str = "INR"
  category: FailureCategory
  source: FailureSource
  stage: str  # authorization/authentication
  reason: str  # payment_failed/insufficient_funds
  error_code: str
  error_description: str
  customer: CustomerProfile
  merchant_id: str
  timestamp: datetime
  metadata: dict = {}

TriageResult:
  recovery_probability: float  # 0.0-1.0
  expected_recovery_paise: int
  priority: Priority
  shap_reason_codes: list[str]  # ["RC01", "RC02"]
  shap_feature_importances: dict[str, float] = {}
  model_version: str = "v1"

GatewayHealthSnapshot:
  bank: str
  rail: str  # UPI/card/netbanking
  state: GatewayHealthState
  success_rate: float
  technical_failure_rate: float
  business_decline_rate: float
  timeout_rate: float
  baseline_success_rate: float
  sample_size: int
  window_minutes: int
  recommended_action: str  # RETRY_NOW / DEFER / REROUTE
  retry_after_seconds: int = 0
  confidence: str = "HIGH"

DiagnosisResult:
  root_cause: str
  is_transient: bool
  failure_category: str
  reasoning: str
  time_sensitivity: str  # immediate/hours/days

StrategyDecision:
  action_type: ActionType
  channel: RecoveryChannel | None = None
  reasoning: str
  retry_delay_seconds: int = 0
  message_content: str | None = None
  payment_link_amount_paise: int | None = None
  escalation_reason: str | None = None
  stopping_reason: str | None = None

RecoveryAction:
  action_id: str
  case_id: str
  action_type: ActionType
  channel: RecoveryChannel | None = None
  status: str  # pending/executing/success/failed
  input_state: dict = {}
  output_result: dict = {}
  cost_paise: int = 0
  timestamp: datetime
  idempotency_key: str

ExperimentAssignment:
  experiment_id: str
  case_id: str
  arm: ExperimentArm
  assigned_at: datetime

ApprovalRecord:
  approval_id: str
  case_id: str
  payment_id: str
  amount_paise: int
  requested_action: ActionType
  agent_recommendation: str
  status: str  # PENDING/APPROVED/REJECTED/EXPIRED
  requested_at: datetime
  expires_at: datetime
  approved_by: str | None = None
  approved_at: datetime | None = None
  decision_channel: str | None = None

AuditLogEntry:
  id: str
  case_id: str
  action_id: str | None = None
  agent_name: str
  step: str
  input_summary: str
  output_summary: str
  reasoning: str
  timestamp: datetime
  guardrails_applied: list[str] = []
  duration_ms: int = 0

RecoveryMetrics:
  total_events: int
  revenue_at_risk_paise: int
  revenue_recovered_paise: int
  recovery_rate: float
  precision: float
  recall: float
  false_positive_cost_paise: int
  avg_time_to_recovery_hours: float
  exceptions_count: int

## File 6: backend/db/__init__.py
Empty.

## File 7: backend/db/database.py
SQLAlchemy async engine setup:
- Create async engine from settings.DATABASE_URL
- Create async_session_maker using async_sessionmaker
- async generator get_db() for FastAPI dependency injection
- DeclarativeBase class
Handle both sqlite+aiosqlite (dev) and postgresql+asyncpg (prod).

## File 8: backend/db/orm_models.py
SQLAlchemy ORM models inheriting from Base:

WebhookEvent: id (UUID as String(36)), razorpay_event_id (String UNIQUE), event_type, payment_id, order_id, raw_payload (JSON), received_at, processed_at, signature_valid (Boolean)

RecoveryCase: id, case_id (String UNIQUE), event_type, status, external_payment_id, external_order_id, amount_paise, currency, failure_category, failure_source, failure_reason, error_code, customer_id, customer_data (JSON), merchant_id, recovery_probability (Float nullable), shap_reason_codes (JSON), experiment_arm, gateway_health_state, retry_count (default 0), last_retry_at, recovered_at, recovered_amount_paise, created_at, updated_at. Indexes on: status, event_type, created_at, experiment_arm.

RecoveryActionRecord: id, case_id (FK), action_type, channel, status, input_state (JSON), output_result (JSON), cost_paise, idempotency_key (UNIQUE), created_at

AuditLog: id, case_id (FK), action_id, agent_name, step, input_summary (Text), output_summary (Text), reasoning (Text), guardrails_applied (JSON), duration_ms, created_at

GatewayHealthRecord: id, bank, rail, state, success_rate, technical_failure_rate, sample_size, snapshot_data (JSON), created_at

Experiment: id, experiment_id (UNIQUE), name, status, control_version, variant_version, variant_split_pct, min_sample_size, started_at

ExperimentAssignmentRecord: id, experiment_id (FK), case_id, arm, assigned_at

ExperimentResultRecord: id, experiment_id (FK), metric, control_value, variant_value, delta, ci_lower, ci_upper, p_value, is_significant, sample_size_control, sample_size_variant, calculated_at

RecoveryApproval: id, approval_id (UNIQUE), case_id, payment_id, amount_paise, requested_action, agent_recommendation, status, requested_at, expires_at, approved_by, approved_at, decision_channel

ChannelBanditState: id, segment (UNIQUE), bandit_state (LargeBinary), updated_at

Use String(36) for UUID columns (SQLite compatible). Use JSON type (works in both SQLite and Postgres).

## File 9: backend/db/schema.sql
PostgreSQL DDL for all tables. UUID, TIMESTAMPTZ, JSONB, TEXT, INTEGER, FLOAT, BOOLEAN. Proper indexes and foreign keys.

## ALSO update the existing .env.example file to include:
GROQ_API_KEY=gsk_your_key_here
OPENROUTER_API_KEY=sk-or-your_key_here
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile
RAZORPAY_KEY_ID=rzp_test_your_key
RAZORPAY_KEY_SECRET=your_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
DATABASE_URL=sqlite+aiosqlite:///./revenueguard.db
REDIS_URL=redis://localhost:6379
HIGH_VALUE_THRESHOLD=5000000
MAX_RETRY_ATTEMPTS=3
EXPERIMENT_VARIANT_PCT=20
N8N_APPROVAL_WEBHOOK_URL=

## Checkpoint:
python -c "from backend.config import get_settings; from backend.models.enums import *; from backend.models.schemas import *; from backend.db.database import Base; from backend.db.orm_models import *; print('All imports OK')"
```

---

## Prompt 2: Razorpay Integration + Webhook Handler

**Model**: GPT-5.5 | **Thinking**: Medium

```
You are building RevenueGuard AI. The foundation (config, models, database) already exists in backend/.

Create the Razorpay integration layer. This uses the REAL razorpay Python SDK for Test Mode integration.

## File 1: backend/integrations/__init__.py
Empty.

## File 2: backend/integrations/razorpay_client.py
Wrapper around the official `razorpay` Python SDK.

Import razorpay and create a client:
  from backend.config import get_settings
  settings = get_settings()
  client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

Methods (all functions, not class methods — keep it simple):
- create_order(amount_paise: int, receipt: str, notes: dict = {}) -> dict
    Calls client.order.create({"amount": amount_paise, "currency": "INR", "receipt": receipt, "notes": notes})

- fetch_payment(payment_id: str) -> dict
    Calls client.payment.fetch(payment_id) — returns full entity with error_code, error_description, error_source, error_step, error_reason.

- fetch_order_payments(order_id: str) -> list[dict]
    Calls client.order.payments(order_id)

- create_payment_link(amount_paise: int, customer_name: str, customer_email: str, customer_phone: str, description: str, notes: dict = {}) -> dict
    Creates a payment link with notify={"sms": True, "email": True}.

- fetch_downtimes() -> list[dict]
    Calls client.payment.downtimes(). Wrap in try/except — may not be available in all test accounts.

- verify_webhook_signature(raw_body: str, signature: str) -> bool
    Calls client.utility.verify_webhook_signature(raw_body, signature, settings.RAZORPAY_WEBHOOK_SECRET)
    Returns True or raises SignatureVerificationError.

## File 3: backend/integrations/normalizer.py
Function: normalize_razorpay_event(raw_event: dict) -> NormalizedFailureEvent

The raw webhook payload:
{
  "event": "payment.failed",
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_xxx",
        "order_id": "order_xxx",
        "amount": 50000,
        "currency": "INR",
        "method": "upi",
        "error_code": "BAD_REQUEST_ERROR",
        "error_description": "Payment failed",
        "error_source": "bank",
        "error_step": "payment_authorization",
        "error_reason": "payment_failed",
        "contact": "+919876543210",
        "email": "customer@example.com",
        "notes": {}
      }
    }
  }
}

CRITICAL category mapping (separates technical from customer issues):
  error_source == "bank" AND error_reason in ("payment_failed", "gateway_error", "server_error") → FailureCategory.SYSTEMIC
  error_source == "bank" AND error_reason in ("insufficient_funds", "incorrect_pin", "card_expired") → FailureCategory.CUSTOMER
  error_source == "customer" → FailureCategory.CUSTOMER
  error_source in ("gateway", "network") → FailureCategory.SYSTEMIC
  error_source == "business" → FailureCategory.BUSINESS
  else → FailureCategory.UNKNOWN

Generate case_id as f"REC-{uuid4().hex[:8].upper()}"
Create CustomerProfile from entity fields.

## File 4: backend/webhooks/__init__.py
Empty.

## File 5: backend/webhooks/razorpay_handler.py
FastAPI APIRouter:

@router.post("/webhooks/razorpay")
async def handle_razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    1. raw_body = await request.body()  # MUST read raw BEFORE any JSON parsing
    2. signature = request.headers.get("X-Razorpay-Signature", "")
    3. Try verify_webhook_signature(raw_body.decode(), signature) — if fails return 400
    4. event = json.loads(raw_body)
    5. razorpay_event_id = event.get("event_id") or request.headers.get("x-razorpay-event-id", str(uuid4()))
    6. Idempotency check: if razorpay_event_id exists in webhook_events table → return {"ok": True, "status": "duplicate"}
    7. Insert WebhookEvent record
    8. If event type is "payment.failed":
       - Normalize via normalize_razorpay_event()
       - Create RecoveryCase in DB with status=DETECTED
       - LPUSH case_id to Redis "recovery_queue"
    9. Return {"ok": True} — MUST respond within 5 seconds total

## File 6: backend/webhooks/checkout_api.py
FastAPI APIRouter for demo:

@router.post("/api/orders")
async def create_demo_order(amount_paise: int = Body(...), receipt: str = Body(default=None)):
    order = create_order(amount_paise, receipt or f"demo-{uuid4().hex[:8]}")
    Return {"order_id": order["id"], "amount": order["amount"], "currency": order["currency"], "key_id": settings.RAZORPAY_KEY_ID}

@router.get("/api/razorpay/status")
async def razorpay_status():
    Try creating a ₹100 order to test connectivity.
    Return {"connected": bool, "environment": "TEST MODE"}

## Checkpoint:
python -c "from backend.integrations.razorpay_client import create_order, verify_webhook_signature; from backend.integrations.normalizer import normalize_razorpay_event; from backend.webhooks.razorpay_handler import router; from backend.webhooks.checkout_api import router as cr; print('Razorpay integration OK')"
```

---

## Prompt 3: Synthetic Data Generator

**Model**: GPT-5.5 | **Thinking**: Medium

```
You are building RevenueGuard AI. Create the synthetic data generator producing 500+ realistic Indian payment failure events.

## File 1: data/generator.py

Class: SyntheticDataGenerator

__init__(self, seed=42, num_events=523): Set seeds, init Faker("en_IN").

generate_batch() -> list[dict]:
  Distribution: 40% SYSTEMIC payment failures (UPI timeout, gateway error), 25% CUSTOMER payment failures (insufficient funds, card expired, wrong PIN), 20% subscription failures, 15% invoice/checkout.

  Each event dict contains:
  - event_id: str(uuid4())
  - event_type: EventType value string
  - razorpay_payment_id: "pay_" + 14 random alphanum
  - razorpay_order_id: "order_" + 14 random alphanum
  - amount_paise: Consumer 70% (₹100-₹10K), B2B 30% (₹5K-₹5L), biased toward ₹200-₹5000
  - currency: "INR"
  - error_source: "bank"|"customer"|"gateway"|"network"|"business"
  - error_step: "payment_authorization"|"payment_authentication"
  - error_reason: matching reason (payment_failed, insufficient_funds, card_expired, gateway_error, etc.)
  - error_code: "BAD_REQUEST_ERROR"|"GATEWAY_ERROR"|"SERVER_ERROR"
  - error_description: human-readable
  - customer: {customer_id, name (Indian via Faker), email, phone (+91...), upi_id (name@bank), preferred_language (40% en, 30% hi, 30% hinglish), lifetime_value_paise, total_transactions, failed_transactions, opted_out (2% True)}
  - merchant_id: "merch_" + 10 alphanum
  - timestamp: last 7 days, biased to 10AM-2PM (30%) and 7PM-11PM (35%)
  - metadata: {payment_method (50% upi, 25% card, 15% netbanking, 10% wallet), card_network, bank_name}
  - ground_truth: {is_recoverable (bool), expected_recovery_method, recovery_difficulty}

  Banks weighted by Indian market share: SBI 20%, HDFC 18%, ICICI 15%, Axis 12%, Kotak 8%, PNB 7%, BOB 5%, others.

  Ground truth rules:
  - UPI timeout + SYSTEMIC → 85% recoverable
  - Gateway error → 90% recoverable
  - Insufficient funds → 60% recoverable
  - Card expired → 70% recoverable
  - Authentication failed → 40% recoverable
  - Wrong PIN → 30% recoverable
  - Mandate revoked → 20% recoverable
  - Business errors → 0% recoverable
  - Opted-out → 0% recoverable

save_batch(filepath): Save as JSON.

generate_for_training() -> tuple[list, list]: Generate 2000, split 80/20 train/test.

## File 2: data/generate_batch.py
CLI: python -m data.generate_batch --output data/test_batch.json --count 523

Uses argparse, calls generator, saves, prints summary.

## Checkpoint:
python -m data.generate_batch --output data/test_batch.json --count 523
python -c "import json; d=json.load(open('data/test_batch.json')); print(f'{len(d)} events, {sum(1 for e in d if e[\"ground_truth\"][\"is_recoverable\"])} recoverable')"
```

---

## Prompt 4: ML Triage Model — Training + Scoring

**Model**: GPT-5.6 Sol | **Thinking**: High

```
You are building RevenueGuard AI. The synthetic data generator (data/generator.py) already exists.

Create the ML triage scoring system. PRINCIPLE: ML scores, LLM reasons. The LLM receives the score as immutable context — it does NOT generate scores.

Architecture reference: Databricks lakebase-fsi-credit-decisioning (LightGBM champion + XGBoost challenger + calibrated LogisticRegression baseline).

## File 1: backend/ml/__init__.py — Empty

## File 2: backend/ml/feature_engineering.py

extract_features(event: dict, gateway_health: dict | None = None) -> dict:

Features (~20):
- amount_paise, amount_log (log10), amount_bucket (0-5 based on ranges)
- failure_category encoded (CUSTOMER=0, SYSTEMIC=1, BUSINESS=2, UNKNOWN=3)
- failure_source encoded (customer=0, bank=1, gateway=2, network=3, business=4)
- payment_method encoded (upi=0, card=1, netbanking=2, wallet=3)
- bank_encoded (label encoded)
- error_reason_encoded (label encoded)
- hour_of_day, day_of_week, is_peak_hours
- customer_lifetime_value_log, customer_total_transactions, customer_failed_transactions, customer_failure_rate
- customer_opted_out (0/1)
- gateway_health_score (default 0.95), gateway_is_degraded (0/1)
- prior_retry_count (default 0)

get_feature_names() -> list[str]: ordered feature name list.

Use sklearn LabelEncoder for bank and error_reason. Save fitted encoders.

## File 3: backend/ml/train_model.py

Offline training script:
1. Import and use SyntheticDataGenerator(num_events=2000).generate_for_training() for train/test split
2. Extract features for each event
3. Labels: ground_truth["is_recoverable"] → binary 0/1
4. Train 3 models:
   a) LightGBM: n_estimators=100, max_depth=6, learning_rate=0.1, class_weight="balanced", verbose=-1
   b) XGBoost: n_estimators=100, max_depth=6, scale_pos_weight=auto, eval_metric="logloss"
   c) CalibratedClassifierCV(LogisticRegression(max_iter=1000, class_weight="balanced"), cv=5)
5. Evaluate on test: AUC-ROC, log-loss, precision, recall, F1 at 0.5 threshold
6. Print comparison table, select champion (highest AUC)
7. SHAP: explainer = shap.TreeExplainer(champion). Save it.
8. Save: models/recovery_model.joblib, models/shap_explainer.joblib, models/feature_names.json, models/label_encoders.joblib
9. Print example SHAP analysis for 3 test events

## File 4: backend/ml/triage_model.py

Class: TriageScorer
__init__: Load model, SHAP explainer, feature names, label encoders from models/
score(event: dict, gateway_health: dict | None = None) -> TriageResult:
  1. extract_features()
  2. predict_proba → recovery_probability
  3. expected_recovery = probability × amount_paise
  4. Priority: CRITICAL (>0.7 + >₹10K), HIGH (>0.5 + >₹1K), MEDIUM (>0.3), LOW (<=0.3)
  5. SHAP reason codes from top 3 features:
     RC01: High failure velocity, RC02: Gateway outage, RC03: Poor recovery history, RC04: High ticket size, RC05: Payment method risk
  6. Return TriageResult

## Checkpoint:
python -m backend.ml.train_model
python -c "from backend.ml.triage_model import TriageScorer; s = TriageScorer(); print('Model loaded, features:', len(s.feature_names))"
```

---

## Prompt 5: Gateway Health Engine

**Model**: GPT-5.5 | **Thinking**: Medium

```
You are building RevenueGuard AI. Create the Gateway Health Engine with Redis sliding-window aggregation and circuit breaker.

Pattern references: Juspay decision-engine (live gateway scores), Resilience4j (circuit breaker states).

## File 1: backend/gateway_health/__init__.py — Empty

## File 2: backend/gateway_health/aggregator.py

Class: GatewayHealthAggregator(__init__(self, redis_client))

Windows: [5, 15, 60] minutes.

async record_outcome(bank, rail, outcome):
  outcome is "success"|"technical_decline"|"business_decline"|"timeout"
  For each window: use Redis sorted sets with timestamp scores.
  Key pattern: gw:{bank}:{rail}:{window}m:{outcome}
  ZADD with timestamp, ZREMRANGEBYSCORE to clean expired entries.

async get_stats(bank, rail, window_minutes=15) -> dict:
  ZCARD each outcome key, compute rates.
  Return {bank, rail, window_minutes, total_attempts, success_rate, technical_failure_rate, business_decline_rate, timeout_rate, sample_size}

async get_all_banks_health() -> list[dict]:
  Scan Redis keys gw:*:*:15m:success to find active bank/rail pairs.
  Return get_stats() for each.

## File 3: backend/gateway_health/circuit_breaker.py

Class: GatewayCircuitBreaker(__init__(self, redis_client, failure_threshold=0.30, min_samples=50, cooldown_seconds=600, probe_count=3, probe_required_successes=2))

State stored in Redis key cb:{bank}:{rail} as JSON.

Transitions:
  CLOSED → OPEN: technical_failure_rate > threshold AND sample_size > min_samples
  OPEN → HALF_OPEN: cooldown elapsed
  HALF_OPEN → CLOSED: probe_successes >= required
  HALF_OPEN → OPEN: probe_failures >= required (double cooldown)

async evaluate(bank, rail, stats) -> GatewayHealthState
async record_probe_result(bank, rail, success: bool)
async get_health(bank, rail, stats) -> GatewayHealthSnapshot:
  Evaluate state, compute recommended_action (RETRY_NOW/DEFER/PROBE), baseline rates, confidence.

## File 4: backend/gateway_health/downtime_monitor.py

Class: DowntimeMonitor

async get_unified_health(bank, rail) -> GatewayHealthSnapshot:
  Get internal health from circuit_breaker.
  Try razorpay_client.fetch_downtimes() — if downtime matches bank, override to OPEN.
  Return worst-of-two signals.

## Checkpoint:
python -c "from backend.gateway_health.aggregator import GatewayHealthAggregator; from backend.gateway_health.circuit_breaker import GatewayCircuitBreaker; from backend.gateway_health.downtime_monitor import DowntimeMonitor; print('Gateway health OK')"
```

---

## Prompt 6: A/B Experiment Framework + MABWiser Channel Bandit

**Model**: GPT-5.6 Terra | **Thinking**: Medium

```
You are building RevenueGuard AI. Create the A/B experiment framework and MAB channel selection bandit.

## File 1: backend/experiments/__init__.py — Empty

## File 2: backend/experiments/assignment.py

import hashlib

def assign_experiment_arm(case_id: str, experiment_id: str = "recovery_agent_v1", variant_pct: int = 20) -> ExperimentArm:
    bucket = int(hashlib.md5(f"{experiment_id}:{case_id}".encode()).hexdigest(), 16) % 100
    return ExperimentArm.TREATMENT if bucket < variant_pct else ExperimentArm.CONTROL

def get_existing_assignment(case_id, experiment_id, db_session) -> ExperimentArm | None:
    Check DB. Return existing arm or None.

## File 3: backend/experiments/baseline.py

Naive rule-based baseline (CONTROL arm):

RETRY_SCHEDULE = [timedelta(minutes=15), timedelta(hours=6), timedelta(hours=24)]

def baseline_decide(case: dict, retry_count: int = 0) -> StrategyDecision:
    if retry_count >= 3: return STOP
    delay = RETRY_SCHEDULE[min(retry_count, 2)]
    return StrategyDecision(action_type=SMART_RETRY, retry_delay_seconds=int(delay.total_seconds()), channel=EMAIL, reasoning=f"Rule-based retry #{retry_count+1}")

## File 4: backend/experiments/analyzer.py

Class: ExperimentAnalyzer

def analyze(experiment_id, control_recovered, control_total, variant_recovered, variant_total) -> dict:
    1. SRM Check: chi-square test — observed vs expected split
       from scipy.stats import chisquare
       expected_total = control_total + variant_total
       srm = chisquare([control_total, variant_total], f_exp=[expected_total*0.8, expected_total*0.2])
       srm_pass = srm.pvalue > 0.01

    2. Two-proportion Z-test:
       from statsmodels.stats.proportion import proportions_ztest
       z_stat, p_value = proportions_ztest([variant_recovered, control_recovered], [variant_total, control_total], alternative='larger')
       
       control_rate = control_recovered / control_total
       variant_rate = variant_recovered / variant_total
       absolute_lift = variant_rate - control_rate
       relative_lift = absolute_lift / control_rate if control_rate > 0 else 0
       
       se = math.sqrt(control_rate*(1-control_rate)/control_total + variant_rate*(1-variant_rate)/variant_total)
       ci_lower = absolute_lift - 1.96 * se
       ci_upper = absolute_lift + 1.96 * se
    
    3. Return dict with all metrics.

## File 5: backend/ml/channel_bandit.py

Class: ChannelBandit

__init__: arms = ["sms", "email", "whatsapp"], segment_bandits dict

get_or_create_bandit(segment) -> MAB:
    Create MAB(arms, LearningPolicy.ThompsonSampling()), fit with uniform prior.

select_channel(segment, eligible_channels=None) -> str:
    Get bandit, predict_expectations(), pick best among eligible.

update(segment, channel, recovered: bool):
    bandit.partial_fit(decisions=[channel], rewards=[1 if recovered else 0])

get_expectations(segment) -> dict[str, float]

segment_customer(customer: dict) -> str:
    Segment by language + LTV bucket + WhatsApp eligibility.
    Return like "en_high_wa" or "hi_low_nowa".

## Checkpoint:
python -c "from backend.experiments.assignment import assign_experiment_arm; print(assign_experiment_arm('test-case-1')); from backend.ml.channel_bandit import ChannelBandit; b = ChannelBandit(); print('Channel:', b.select_channel('en_high_wa')); print('OK')"
```

---

## Prompt 7: LangGraph Agent Core

**Model**: GPT-5.6 Sol | **Thinking**: High

```
You are building RevenueGuard AI. Create the LangGraph multi-agent system. All prior components exist (config, models, ML scorer, gateway health, experiments, channel bandit).

CRITICAL PRINCIPLES:
- LLM handles: root-cause reasoning, natural-language explanation, message drafting
- Deterministic components handle: ML scoring, gateway health, experiment assignment, policy enforcement
- The LLM NEVER outputs the recovery probability. It RECEIVES it as immutable context.
- LLM provider is Groq (langchain-groq, model llama-3.3-70b-versatile). Fallback: OpenRouter via langchain-openai with custom base_url.

## File 1: backend/agents/__init__.py — Empty

## File 2: backend/agents/state.py
RecoveryState(TypedDict):
  case_id: str
  case_data: dict
  triage: dict | None
  gateway_health: dict | None
  experiment_arm: str | None
  diagnosis: dict | None
  strategy: dict | None
  selected_channel: str | None
  actions: list[dict]
  needs_approval: bool
  approval_status: str | None
  audit_trail: list[dict]
  error: str | None
  final_decision: str | None

## File 3: backend/agents/llm_client.py
Helper to create LLM client based on config:

def get_llm():
    settings = get_settings()
    if settings.LLM_PROVIDER == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=settings.LLM_MODEL,
            temperature=0.1,
            max_tokens=1024,
        )
    elif settings.LLM_PROVIDER == "openrouter":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            model=settings.LLM_MODEL,
            temperature=0.1,
            max_tokens=1024,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")

## File 4: backend/agents/graph.py
LangGraph StateGraph:

Nodes: enrich_ml, enrich_health, assign_experiment, baseline_decide, agent_diagnose, agent_strategize, select_channel, policy_check, request_approval, execute_action, log_audit

Edges:
START → enrich_ml → enrich_health → assign_experiment → (conditional)
  CONTROL → baseline_decide → policy_check
  TREATMENT → agent_diagnose → agent_strategize → select_channel → policy_check
policy_check → (conditional)
  needs_approval=True → request_approval → log_audit → END
  action_type=STOP → log_audit → END
  else → execute_action → log_audit → END

def build_recovery_graph() -> CompiledStateGraph:
    Build and compile the graph. Return it.

## File 5: backend/agents/triage_node.py
async def enrich_with_ml(state) -> dict:
    Score with TriageScorer. Add to audit_trail. Return {"triage": result_dict}

## File 6: backend/agents/health_node.py
async def enrich_with_health(state) -> dict:
    Get gateway health for the bank/rail from the event. Return {"gateway_health": snapshot_dict}
    If Redis unavailable, return default healthy snapshot.

## File 7: backend/agents/experiment_node.py
async def assign_experiment(state) -> dict:
    Call assign_experiment_arm(case_id). Return {"experiment_arm": arm.value}

## File 8: backend/agents/diagnosis_node.py
async def agent_diagnose(state) -> dict:
    Use get_llm() from llm_client.py.
    
    Build prompt with ML score + gateway health as IMMUTABLE CONTEXT:
    "You are a payment failure diagnostic agent for Indian payment infrastructure.
    
    CONTEXT (DO NOT modify these values — they come from deterministic ML systems):
    - Recovery Probability: {triage.recovery_probability} (from LightGBM model)
    - SHAP Reason Codes: {triage.shap_reason_codes}
    - Gateway Health: {bank} {rail} — {state} (success rate: {success_rate}, baseline: {baseline})
    
    PAYMENT FAILURE:
    - Amount: ₹{amount/100}
    - Error Source: {source}, Step: {stage}, Reason: {reason}
    - Description: {error_description}
    - Payment Method: {payment_method}, Bank: {bank_name}
    
    Analyze the root cause. Output ONLY valid JSON:
    {\"root_cause\": \"...\", \"is_transient\": true/false, \"failure_category\": \"CUSTOMER_ACTION_NEEDED|SYSTEMIC_WAIT|PERMANENT_FAILURE\", \"reasoning\": \"...\", \"time_sensitivity\": \"immediate|hours|days\"}"
    
    Parse JSON response. Add to audit_trail. Return {"diagnosis": result_dict}

## File 9: backend/agents/strategy_node.py
async def agent_strategize(state) -> dict:
    DETERMINISTIC OVERRIDES (checked BEFORE calling LLM):
    1. gateway_health.state == "OPEN" → DEFER with retry_after from health
    2. customer.opted_out → STOP
    3. retry_count >= MAX → STOP
    4. category == "BUSINESS" → ESCALATE
    
    If no override, call LLM:
    "You are a recovery strategy agent. Given the diagnosis and context, choose ONE action:
    SMART_RETRY, PAYMENT_LINK, NUDGE_EMAIL, NUDGE_SMS, NUDGE_WHATSAPP, DEFER, ESCALATE_HUMAN, STOP
    
    Output JSON: {\"action_type\": \"...\", \"reasoning\": \"...\", \"retry_delay_seconds\": 0, \"message_content\": \"...\"}"

## File 10: backend/agents/channel_node.py
async def select_channel(state) -> dict:
    If nudge action, use ChannelBandit to pick best channel among eligible.
    Override strategy's channel. Return {"strategy": updated, "selected_channel": chosen}

## File 11: backend/agents/execution_node.py
async def execute_action(state) -> dict:
    Execute: create payment link / log notification / log escalation / log stop.
    Create RecoveryAction with idempotency_key. Return {"actions": updated_list}

## File 12: backend/guardrails/__init__.py — Empty

## File 13: backend/guardrails/policy_engine.py
Class PolicyEngine:
  check_all(state) -> tuple[bool, str | None]: Run all checks.
  needs_approval(state) -> bool: amount > HIGH_VALUE_THRESHOLD
  
  Checks: opt_out, retry_limit, cooldown, quiet_hours (9PM-9AM IST), recovery_cost (amount < ₹100)
  
  Backend DOUBLE-CHECKS approval: if amount > threshold AND no valid unexpired approval → raise ApprovalRequired

async def policy_check_node(state) -> dict:
    Run checks. If blocked → force STOP. If needs approval → set needs_approval=True.

## File 14: backend/guardrails/hitl_gate.py
async def request_approval_node(state) -> dict:
    Create PENDING ApprovalRecord (expires in 2h).
    If N8N_APPROVAL_WEBHOOK_URL set, POST to n8n with case details.
    Return {"approval_status": "PENDING"}

## Checkpoint:
python -c "from backend.agents.graph import build_recovery_graph; g = build_recovery_graph(); print(f'Graph nodes: {list(g.get_graph().nodes)}'); print('LangGraph OK')"
```

---

## Prompt 8: FastAPI Backend + Worker

**Model**: GPT-5.6 Terra | **Thinking**: Medium

```
You are building RevenueGuard AI. Create the FastAPI app and background worker. All components exist.

## File 1: backend/api/__init__.py — Empty

## File 2: backend/api/main.py
FastAPI app. Include routers from webhooks/razorpay_handler and webhooks/checkout_api.

Endpoints:

GET /api/health → {"status": "ok", "environment": settings.APP_ENV}

GET /api/cases?status=&page=1&page_size=20&experiment_arm= → paginated cases list

GET /api/cases/{case_id} → full detail with triage, gateway_health, actions, audit_trail, timeline

GET /api/metrics → aggregate: total_events, revenue_at_risk, revenue_recovered, recovery_rate, breakdown by experiment arm

GET /api/gateway-health → current health for all banks/rails

GET /api/experiments/{experiment_id}/results → call ExperimentAnalyzer, return results

POST /api/approvals/{approval_id}/approve (body: {approved_by}) → update approval, re-enqueue case
POST /api/approvals/{approval_id}/reject → update approval

POST /api/simulate/batch (body: {count: 50}) → generate synthetic events, create cases, enqueue to Redis
POST /api/simulate/outage (body: {bank: "SBI", rail: "UPI"}) → inject failure events to trigger circuit breaker

WebSocket /ws/events → stream new events to connected clients

CORS: allow all origins in dev.

Startup: create tables (Base.metadata.create_all), init Redis, create default experiment.

## File 3: backend/worker.py
async def process_case(case_id):
    Fetch case from DB, build RecoveryState, invoke graph, update DB with results, save actions+audit, broadcast via WebSocket.

async def worker_loop():
    BRPOP recovery_queue with 5s timeout. Process each case. Print progress.

if __name__ == "__main__": asyncio.run(worker_loop())

## File 4: Update pyproject.toml with a [project.scripts] section or just document:
  # Start API: python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
  # Start worker: python -m backend.worker

## Checkpoint:
docker compose up -d  # Postgres + Redis
python -m uvicorn backend.api.main:app --port 8000 &
python -m backend.worker &
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/simulate/batch -H "Content-Type: application/json" -d "{\"count\": 5}"
sleep 15
curl http://localhost:8000/api/cases
curl http://localhost:8000/api/metrics
```

---

## Prompt 9: Next.js Frontend Dashboard

**Model**: GPT-5.6 Terra | **Thinking**: Medium

```
You are building RevenueGuard AI. Create the Next.js 14 dashboard frontend.

First run these setup commands:
  npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
  cd frontend
  npx shadcn@latest init -d
  npx shadcn@latest add card button badge table tabs separator skeleton alert input label select
  npm install @tanstack/react-query recharts axios

Then create these files:

## frontend/src/lib/api.ts
Axios client pointing to NEXT_PUBLIC_API_URL (default http://localhost:8000).
Functions: getCases, getCase, getMetrics, getGatewayHealth, getExperimentResults, simulateBatch, simulateOutage, createOrder.

## frontend/src/lib/types.ts
TypeScript types matching backend Pydantic schemas.

## frontend/src/app/layout.tsx
Root layout with sidebar navigation. Links: Control Room (/), Sandbox (/sandbox), Cases (/cases), Experiments (/experiments), Gateway Health (/gateway-health). Dark theme support. Use "RevenueGuard AI" branding.

## frontend/src/app/page.tsx — Control Room
"Simulation control room" feel. Layout:

Top: 4 metric cards — Active Failed Payments, Revenue at Risk (₹), Revenue Recovered (₹), Recovery Rate (%)
Use Indian number formatting: ₹1,23,456

Middle-left: Gateway Health Map — bars for SBI/HDFC/ICICI/Axis/Kotak/PNB. Color: green=HEALTHY, yellow=DEGRADED, red=OPEN. Show "success_rate% | sample_size attempts"

Middle-right: Experiment Snapshot — two bars (Baseline vs Agent), lift value, p-value badge, SIGNIFICANT/NOT_SIGNIFICANT status

Bottom: Action buttons [Run Recovery Batch] [Simulate SBI Outage] [Inspect Random Case] + recent events feed (auto-refresh every 5s)

## frontend/src/app/sandbox/page.tsx — Live Razorpay Sandbox
Left panel: Razorpay connection status + Create Payment form (amount, auto-gen case ID). [Create Razorpay Order] button. After creation show order_id. Instructions for failure@razorpay.

Right panel: Webhook event display with verification checklist (✓ Received, ✓ Signature verified, ✓ Deduplicated, ✓ Recovery started). Payment error details. Recovery engine results.

## frontend/src/app/cases/page.tsx — Cases table with filters
## frontend/src/app/cases/[id]/page.tsx — Timeline + agent trace + SHAP codes
## frontend/src/app/experiments/page.tsx — Full A/B dashboard matching research mockup
## frontend/src/app/gateway-health/page.tsx — Full health map with circuit states

Auto-refresh gateway health and events every 5 seconds via React Query refetchInterval.
Make it responsive. Use proper ₹ formatting throughout.
```

---

## Prompt 10: Evaluation Pipeline + Docker + Deployment

**Model**: GPT-5.5 | **Thinking**: Medium

```
You are building RevenueGuard AI. Create evaluation pipeline, Docker config, and Render deployment files.

## File 1: evals/__init__.py — Empty

## File 2: evals/batch_runner.py
Class BatchEvaluator:
  run(batch_path="data/test_batch.json", output_dir="evals/results") -> dict:
    Load batch. For each event: normalize, ML score, simulate gateway health, assign experiment, run baseline or agent (simplified — direct node calls without full LangGraph for speed), compare against ground_truth.
    
    Calculate: total_events, revenue_at_risk, TP/FP/FN/TN, precision, recall, F1, simulated recovery, false_positive_cost.
    A/B comparison with ExperimentAnalyzer.
    
    Print formatted report:
    ═══════════════════════════════════════
    REVENUEGUARD AI — BATCH EVALUATION
    ═══════════════════════════════════════
    Dataset: 523 events
    Revenue at Risk: ₹18,47,230
    ML Precision: 69.7% | Recall: 82.3% | F1: 75.4%
    Recovered (simulated): ₹12,83,450 (69.5%)
    FP Cost: ₹2,340
    Baseline: 21.0% | Agent: 26.8% | Lift: +5.8pp | p=0.003
    ═══════════════════════════════════════
    
    Save to output_dir as JSON files.

CLI: python -m evals.batch_runner

## File 3: docker-compose.yml
postgres (16-alpine, port 5432, db=revenueguard) + redis (7-alpine, port 6379). Healthchecks. Named volume for postgres data.

## File 4: Dockerfile
Multi-stage:
  Stage 1: node:22-alpine — build frontend (npm ci, npm run build with output: 'export')
  Stage 2: python:3.11-slim — copy built frontend to /app/static, copy backend+models+data, pip install deps
  CMD: uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT

## File 5: render.yaml
Render Blueprint:
  services:
    - type: web, name: revenueguard-api, env: python, buildCommand: "pip install -r requirements.txt", startCommand: "uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT"
    - type: worker, name: revenueguard-worker, env: python, startCommand: "python -m backend.worker"
  databases:
    - name: revenueguard-db, plan: free
  keyValueStores:  
    - name: revenueguard-redis, plan: free

## File 6: .env.example — updated with all variables and descriptions

## File 7: README.md
Professional README:
- Title: "RevenueGuard AI — Intelligent Payment Recovery Agent"
- One-liner: "Multi-agent system that detects revenue at risk, diagnoses root cause, and executes recovery"
- 🔴 Live Demo placeholder
- Architecture mermaid diagram
- Features: Real Razorpay Integration, ML Triage (LightGBM+SHAP), Gateway Health Intelligence, A/B Experimentation, Thompson Sampling Channel Selection, HITL Approval
- Tech stack table
- Quick Start: docker compose up, python -m uvicorn..., python -m backend.worker, cd frontend && npm run dev
- Eval results summary
- Innovation highlights
- "What Broke" section placeholder

## Checkpoint:
docker compose up -d
python -m evals.batch_runner
# Should print full formatted evaluation report
```

---

## Summary: Execution Cheat Sheet

| # | Prompt | Codex Model | Thinking | Est. Time |
|---|--------|-------------|----------|-----------|
| 1 | Foundation (config/models/DB) | GPT-5.5 | Medium | 45 min |
| 2 | Razorpay SDK + Webhook | GPT-5.5 | Medium | 30 min |
| 3 | Synthetic Data Generator | GPT-5.5 | Medium | 30 min |
| 4 | ML Triage (LightGBM+SHAP) | **GPT-5.6 Sol** | **High** | 45 min |
| 5 | Gateway Health Engine | GPT-5.5 | Medium | 30 min |
| 6 | A/B Framework + MABWiser | GPT-5.6 Terra | Medium | 30 min |
| 7 | LangGraph Agent Core | **GPT-5.6 Sol** | **High** | 45 min |
| 8 | FastAPI Backend + Worker | GPT-5.6 Terra | Medium | 45 min |
| 9 | Next.js Dashboard | GPT-5.6 Terra | Medium | 60 min |
| 10 | Eval + Docker + Deploy | GPT-5.5 | Medium | 30 min |

> [!CAUTION]
> **Always run the checkpoint command** at the end of each prompt before moving to the next. If a checkpoint fails, fix the issue in the same Codex session before proceeding.
>
> **GPT-5.6 Sol is reserved for Prompts 4 and 7** — these are the complex tasks requiring deep reasoning (ML training pipeline and multi-agent LangGraph with Groq integration). All other prompts work well with GPT-5.5 or Terra.
