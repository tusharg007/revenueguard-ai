from datetime import datetime, timezone
from uuid import uuid4

from backend.models.enums import EventType, FailureCategory, FailureSource
from backend.models.schemas import CustomerProfile, NormalizedFailureEvent


# Razorpay error_reason -> FailureCategory mapping
_BANK_SYSTEMIC_REASONS = {"payment_failed", "gateway_error", "server_error"}
_BANK_CUSTOMER_REASONS = {"insufficient_funds", "incorrect_pin", "card_expired"}


def _classify_failure(error_source: str, error_reason: str) -> FailureCategory:
    """Classify failure as SYSTEMIC vs CUSTOMER vs BUSINESS.
    This separation is CRITICAL:
    - SYSTEMIC (bank timeout, gateway error) -> defer/retry later
    - CUSTOMER (insufficient funds, wrong PIN) -> nudge customer
    - BUSINESS -> escalate to merchant
    """
    reason_lower = error_reason.lower() if error_reason else ""
    source_lower = error_source.lower() if error_source else ""

    if source_lower == "bank":
        if reason_lower in _BANK_SYSTEMIC_REASONS:
            return FailureCategory.SYSTEMIC
        if reason_lower in _BANK_CUSTOMER_REASONS:
            return FailureCategory.CUSTOMER
    if source_lower == "customer":
        return FailureCategory.CUSTOMER
    if source_lower in ("gateway", "network"):
        return FailureCategory.SYSTEMIC
    if source_lower == "business":
        return FailureCategory.BUSINESS
    return FailureCategory.UNKNOWN


def _map_source(error_source: str) -> FailureSource:
    mapping = {
        "customer": FailureSource.CUSTOMER,
        "bank": FailureSource.BANK,
        "gateway": FailureSource.GATEWAY,
        "network": FailureSource.NETWORK,
        "business": FailureSource.BUSINESS,
    }
    return mapping.get(error_source.lower(), FailureSource.UNKNOWN) if error_source else FailureSource.UNKNOWN


def _map_event_type(event_name: str) -> EventType:
    mapping = {
        "payment.failed": EventType.PAYMENT_FAILED,
        "subscription.halted": EventType.SUBSCRIPTION_HALTED,
        "subscription.pending": EventType.SUBSCRIPTION_PENDING,
        "checkout.abandoned": EventType.CHECKOUT_ABANDONED,
        "invoice.expired": EventType.INVOICE_EXPIRED,
        "invoice.overdue": EventType.INVOICE_OVERDUE,
    }
    return mapping.get(event_name, EventType.PAYMENT_FAILED)


def normalize_razorpay_event(raw_event: dict) -> NormalizedFailureEvent:
    """Convert raw Razorpay webhook payload to processor-agnostic NormalizedFailureEvent."""
    event_name = raw_event.get("event", "payment.failed")
    payload = raw_event.get("payload", {})

    # Extract payment entity (handles both payment.failed and other event types)
    payment_entity = {}
    if "payment" in payload:
        payment_entity = payload["payment"].get("entity", {})
    elif "subscription" in payload:
        payment_entity = payload["subscription"].get("entity", {})
    elif "invoice" in payload:
        payment_entity = payload["invoice"].get("entity", {})

    error_source = payment_entity.get("error_source", "unknown")
    error_reason = payment_entity.get("error_reason", "unknown")
    error_step = payment_entity.get("error_step", "payment_authorization")
    error_code = payment_entity.get("error_code", "UNKNOWN_ERROR")
    error_description = payment_entity.get("error_description", "Payment failed")

    case_id = f"REC-{uuid4().hex[:8].upper()}"

    # Build customer profile from available data
    contact = payment_entity.get("contact", "+910000000000")
    email = payment_entity.get("email", "unknown@example.com")
    notes = payment_entity.get("notes", {})
    customer = CustomerProfile(
        customer_id=notes.get("customer_id", f"CUST-{uuid4().hex[:6].upper()}"),
        name=notes.get("customer_name", "Unknown Customer"),
        email=email,
        phone=contact,
        upi_id=payment_entity.get("vpa"),  # UPI VPA if available
    )

    return NormalizedFailureEvent(
        case_id=case_id,
        event_type=_map_event_type(event_name),
        processor="razorpay",
        external_payment_id=payment_entity.get("id", ""),
        external_order_id=payment_entity.get("order_id"),
        amount_paise=payment_entity.get("amount", 0),
        currency=payment_entity.get("currency", "INR"),
        category=_classify_failure(error_source, error_reason),
        source=_map_source(error_source),
        stage=error_step,
        reason=error_reason,
        error_code=error_code,
        error_description=error_description,
        customer=customer,
        merchant_id=notes.get("merchant_id", "default_merchant"),
        timestamp=datetime.now(timezone.utc),
        metadata={
            "payment_method": payment_entity.get("method", "unknown"),
            "bank_name": payment_entity.get("bank", "unknown"),
            "card_network": payment_entity.get("network"),
            "wallet": payment_entity.get("wallet"),
            "vpa": payment_entity.get("vpa"),
        },
    )
