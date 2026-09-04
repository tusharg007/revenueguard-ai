import razorpay

from backend.config import get_settings

settings = get_settings()
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_order(amount_paise: int, receipt: str, notes: dict | None = None) -> dict:
    """Create a real Razorpay test order."""
    data = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
        "notes": notes or {},
    }
    return client.order.create(data=data)


def fetch_payment(payment_id: str) -> dict:
    """Fetch full payment entity with error fields."""
    return client.payment.fetch(payment_id)


def fetch_order_payments(order_id: str) -> list[dict]:
    """Get all payment attempts for an order."""
    result = client.order.payments(order_id)
    return result.get("items", [])


def create_payment_link(
    amount_paise: int,
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    description: str,
    notes: dict | None = None,
) -> dict:
    """Create a Razorpay payment link for recovery."""
    data = {
        "amount": amount_paise,
        "currency": "INR",
        "description": description,
        "customer": {
            "name": customer_name,
            "email": customer_email,
            "contact": customer_phone,
        },
        "notify": {"sms": True, "email": True},
        "accept_partial": False,
        "notes": notes or {},
    }
    return client.payment_link.create(data=data)


def fetch_downtimes() -> list[dict]:
    """Fetch real-time Razorpay-reported payment downtimes."""
    try:
        result = client.payment.downtimes()
        return result if isinstance(result, list) else result.get("items", [])
    except Exception:
        return []


def verify_webhook_signature(raw_body: str, signature: str) -> bool:
    """Verify webhook HMAC-SHA256 signature using Razorpay SDK."""
    client.utility.verify_webhook_signature(raw_body, signature, settings.RAZORPAY_WEBHOOK_SECRET)
    return True
