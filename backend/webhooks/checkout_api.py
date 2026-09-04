import logging
from uuid import uuid4

from fastapi import APIRouter, Body, HTTPException

from backend.config import get_settings
from backend.integrations.razorpay_client import create_order

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/orders")
async def create_demo_order(
    amount_paise: int = Body(...),
    receipt: str | None = Body(default=None),
):
    """Create a real Razorpay test order for the Live Sandbox demo."""
    settings = get_settings()
    receipt = receipt or f"demo-{uuid4().hex[:8]}"

    try:
        order = create_order(amount_paise=amount_paise, receipt=receipt)
        return {
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key_id": settings.RAZORPAY_KEY_ID,
            "receipt": receipt,
        }
    except Exception as e:
        logger.error(f"Failed to create Razorpay order: {e}")
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/api/razorpay/status")
async def razorpay_status():
    """Check Razorpay API connectivity."""
    settings = get_settings()
    try:
        # Try creating a small test order to verify connectivity
        order = create_order(amount_paise=100, receipt=f"health-{uuid4().hex[:6]}")
        return {
            "connected": True,
            "environment": "TEST MODE",
            "key_id": settings.RAZORPAY_KEY_ID[:12] + "...",
            "test_order_id": order["id"],
        }
    except Exception as e:
        return {
            "connected": False,
            "environment": "TEST MODE",
            "error": str(e),
        }
