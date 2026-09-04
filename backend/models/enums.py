from enum import Enum


class EventType(str, Enum):
    PAYMENT_FAILED = "payment_failed"
    SUBSCRIPTION_HALTED = "subscription_halted"
    SUBSCRIPTION_PENDING = "subscription_pending"
    CHECKOUT_ABANDONED = "checkout_abandoned"
    INVOICE_EXPIRED = "invoice_expired"
    INVOICE_OVERDUE = "invoice_overdue"


class EventStatus(str, Enum):
    DETECTED = "detected"
    TRIAGING = "triaging"
    DIAGNOSING = "diagnosing"
    STRATEGIZING = "strategizing"
    EXECUTING = "executing"
    RECOVERED = "recovered"
    FAILED = "failed"
    ESCALATED = "escalated"
    STOPPED = "stopped"


class FailureCategory(str, Enum):
    CUSTOMER = "customer"
    SYSTEMIC = "systemic"
    BUSINESS = "business"
    UNKNOWN = "unknown"


class FailureSource(str, Enum):
    CUSTOMER = "customer"
    BANK = "bank"
    GATEWAY = "gateway"
    NETWORK = "network"
    BUSINESS = "business"
    RAZORPAY = "razorpay"
    UNKNOWN = "unknown"


class ActionType(str, Enum):
    SMART_RETRY = "smart_retry"
    PAYMENT_LINK = "payment_link"
    NUDGE_EMAIL = "nudge_email"
    NUDGE_SMS = "nudge_sms"
    NUDGE_WHATSAPP = "nudge_whatsapp"
    ESCALATE_HUMAN = "escalate_human"
    DEFER = "defer"
    STOP = "stop"


class RecoveryChannel(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    IN_APP = "in_app"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GatewayHealthState(str, Enum):
    """Circuit breaker states. CLOSED = healthy (traffic flows)."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ExperimentArm(str, Enum):
    CONTROL = "control"
    TREATMENT = "treatment"
