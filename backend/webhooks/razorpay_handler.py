import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.db.database import get_db
from backend.db.orm_models import RecoveryCase, WebhookEvent
from backend.models.enums import EventStatus
from backend.redis_client import create_redis_client
from backend.integrations.normalizer import normalize_razorpay_event
from backend.integrations.razorpay_client import verify_webhook_signature

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhooks/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive Razorpay webhooks. MUST respond within 5 seconds.
    
    Flow:
    1. Read raw body (before JSON parsing to preserve signature)
    2. Verify HMAC-SHA256 signature
    3. Deduplicate via x-razorpay-event-id
    4. Persist event
    5. Enqueue for background processing
    6. Return 200
    """
    settings = get_settings()

    # 1. Read raw body BEFORE any JSON parsing
    raw_body = await request.body()
    raw_body_str = raw_body.decode("utf-8")

    # 2. Verify signature when webhook verification is configured.
    signature = request.headers.get("X-Razorpay-Signature", "")
    if settings.RAZORPAY_WEBHOOK_SECRET and signature:
        try:
            verify_webhook_signature(raw_body_str, signature)
        except Exception as e:
            logger.warning(f"Webhook signature verification failed: {e}")
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "Invalid signature"},
            )
    elif settings.RAZORPAY_WEBHOOK_SECRET:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Missing signature"},
        )

    # 3. Parse event
    try:
        event = json.loads(raw_body_str)
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Invalid JSON"})

    # 4. Idempotency check via event ID
    razorpay_event_id = (
        event.get("event_id")
        or request.headers.get("x-razorpay-event-id")
        or str(uuid4())
    )

    existing = await db.execute(
        select(WebhookEvent).where(WebhookEvent.razorpay_event_id == razorpay_event_id)
    )
    if existing.scalar_one_or_none():
        return {"ok": True, "status": "duplicate"}

    # 5. Persist webhook event
    event_type = event.get("event", "unknown")
    payment_entity = event.get("payload", {}).get("payment", {}).get("entity", {})

    webhook_record = WebhookEvent(
        razorpay_event_id=razorpay_event_id,
        event_type=event_type,
        payment_id=payment_entity.get("id"),
        order_id=payment_entity.get("order_id"),
        raw_payload=event,
        signature_valid=True,
    )
    db.add(webhook_record)

    # 6. If payment.failed, create recovery case and enqueue
    if event_type == "payment.failed":
        normalized = normalize_razorpay_event(event)

        customer_data = normalized.customer.model_dump(mode="json")
        customer_data["_revenueguard_context"] = {
            "metadata": normalized.metadata,
            "error_description": normalized.error_description,
        }
        case = RecoveryCase(
            case_id=normalized.case_id,
            event_type=normalized.event_type.value,
            status=EventStatus.DETECTED.value,
            external_payment_id=normalized.external_payment_id,
            external_order_id=normalized.external_order_id,
            amount_paise=normalized.amount_paise,
            currency=normalized.currency,
            failure_category=normalized.category.value,
            failure_source=normalized.source.value,
            failure_reason=normalized.reason,
            error_code=normalized.error_code,
            customer_id=normalized.customer.customer_id,
            customer_data=customer_data,
            merchant_id=normalized.merchant_id,
        )
        db.add(case)
        await db.commit()

        # Enqueue to Redis for background processing
        try:
            redis_client = create_redis_client(settings.REDIS_URL)
            await redis_client.lpush("recovery_queue", normalized.case_id)
            await redis_client.aclose()
        except Exception as e:
            logger.warning(f"Redis enqueue failed (will process later): {e}")

    return {"ok": True}
