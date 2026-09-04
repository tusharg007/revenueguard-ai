import json
import math
import random
import string
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from faker import Faker

from backend.models.enums import EventType


class SyntheticDataGenerator:
    """Generate realistic Indian payment failure events for RevenueGuard AI."""

    BANKS = [
        ("SBI", 0.20),
        ("HDFC", 0.18),
        ("ICICI", 0.15),
        ("Axis", 0.12),
        ("Kotak", 0.08),
        ("PNB", 0.07),
        ("BOB", 0.05),
        ("Canara", 0.04),
        ("Union Bank", 0.04),
        ("IDFC First", 0.03),
        ("Yes Bank", 0.02),
        ("Federal Bank", 0.02),
    ]
    PAYMENT_METHODS = [("upi", 0.50), ("card", 0.25), ("netbanking", 0.15), ("wallet", 0.10)]
    CARD_NETWORKS = [("Visa", 0.40), ("Mastercard", 0.35), ("RuPay", 0.25)]
    LANGUAGES = [("en", 0.40), ("hi", 0.30), ("hinglish", 0.30)]
    UPI_HANDLES = ["sbi", "hdfc", "icici", "axisbank", "kotak", "paytm", "okhdfcbank", "ybl"]
    EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "rediffmail.com"]

    SYSTEMIC_FAILURES = [
        (
            "bank",
            "payment_authorization",
            "payment_failed",
            "BAD_REQUEST_ERROR",
            "Payment failed at the bank due to a temporary issue",
        ),
        (
            "bank",
            "payment_authorization",
            "gateway_error",
            "GATEWAY_ERROR",
            "The bank gateway was temporarily unavailable",
        ),
        (
            "bank",
            "payment_authorization",
            "server_error",
            "SERVER_ERROR",
            "The bank server did not respond in time",
        ),
        (
            "network",
            "payment_authorization",
            "timeout",
            "SERVER_ERROR",
            "UPI payment timed out before authorization completed",
        ),
        (
            "gateway",
            "payment_authorization",
            "gateway_error",
            "GATEWAY_ERROR",
            "The payment gateway returned a temporary error",
        ),
    ]
    CUSTOMER_FAILURES = [
        (
            "bank",
            "payment_authorization",
            "insufficient_funds",
            "BAD_REQUEST_ERROR",
            "Payment failed because the account has insufficient funds",
        ),
        (
            "bank",
            "payment_authentication",
            "incorrect_pin",
            "BAD_REQUEST_ERROR",
            "Payment failed because an incorrect PIN was entered",
        ),
        (
            "bank",
            "payment_authentication",
            "card_expired",
            "BAD_REQUEST_ERROR",
            "Payment failed because the card has expired",
        ),
        (
            "customer",
            "payment_authentication",
            "authentication_failed",
            "BAD_REQUEST_ERROR",
            "Payment authentication failed",
        ),
    ]
    SUBSCRIPTION_FAILURES = [
        (
            "customer",
            "payment_authentication",
            "mandate_revoked",
            "BAD_REQUEST_ERROR",
            "The customer revoked the recurring payment mandate",
        ),
        (
            "bank",
            "payment_authorization",
            "insufficient_funds",
            "BAD_REQUEST_ERROR",
            "Recurring payment failed because the account has insufficient funds",
        ),
        (
            "gateway",
            "payment_authorization",
            "gateway_error",
            "GATEWAY_ERROR",
            "Recurring payment failed due to a temporary gateway error",
        ),
    ]
    INVOICE_CHECKOUT_FAILURES = [
        (
            "customer",
            "payment_authentication",
            "authentication_failed",
            "BAD_REQUEST_ERROR",
            "Customer did not complete payment authentication",
        ),
        (
            "business",
            "payment_authorization",
            "business_rule_violation",
            "BAD_REQUEST_ERROR",
            "Transaction was blocked by merchant business rules",
        ),
        (
            "gateway",
            "payment_authorization",
            "gateway_error",
            "GATEWAY_ERROR",
            "Checkout payment failed due to a gateway error",
        ),
    ]

    def __init__(self, seed: int = 42, num_events: int = 523):
        self.seed = seed
        self.num_events = num_events
        self.fake = Faker("en_IN")
        random.seed(seed)
        Faker.seed(seed)

    def _weighted_choice(self, weighted_items: list[tuple[str, float]]) -> str:
        values, weights = zip(*weighted_items)
        return random.choices(values, weights=weights, k=1)[0]

    def _id_suffix(self, length: int) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(random.choices(alphabet, k=length))

    def _generate_amount_paise(self) -> int:
        if random.random() < 0.30:
            amount = int(random.lognormvariate(math.log(1_500_000), 1.0))
            return max(500_000, min(50_000_000, amount))

        amount = int(random.lognormvariate(math.log(80_000), 0.9))
        return max(10_000, min(1_000_000, amount))

    def _generate_timestamp(self) -> str:
        base = datetime.now(timezone.utc) - timedelta(
            days=random.uniform(0, 7),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )
        bucket = random.random()
        if bucket < 0.30:
            hour = random.randint(10, 13)
        elif bucket < 0.65:
            hour = random.randint(19, 22)
        else:
            hour = random.choice([0, 1, 6, 7, 8, 9, 14, 15, 16, 17, 18, 23])
        timestamp = base.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))
        return timestamp.isoformat()

    def _generate_customer(self, payment_method: str) -> dict:
        first_name = self.fake.first_name()
        last_name = self.fake.last_name()
        local_part = f"{first_name}.{last_name}".lower().replace(" ", "")
        phone_start = random.choice(["6", "7", "8", "9"])

        upi_id = None
        if payment_method == "upi":
            upi_id = f"{local_part}@{random.choice(self.UPI_HANDLES)}"

        total_transactions = random.randint(1, 240)
        failed_transactions = random.randint(0, min(24, total_transactions))

        return {
            "customer_id": f"cust_{self._id_suffix(10)}",
            "name": f"{first_name} {last_name}",
            "email": f"{local_part}@{random.choice(self.EMAIL_DOMAINS)}",
            "phone": f"+91{phone_start}{random.randint(100000000, 999999999)}",
            "upi_id": upi_id,
            "preferred_language": self._weighted_choice(self.LANGUAGES),
            "lifetime_value_paise": random.randint(20_000, 20_000_000),
            "total_transactions": total_transactions,
            "failed_transactions": failed_transactions,
            "opted_out": random.random() < 0.02,
        }

    def _ground_truth(
        self,
        error_source: str,
        error_reason: str,
        payment_method: str,
        is_systemic_bucket: bool,
        opted_out: bool,
    ) -> dict:
        if opted_out or error_source == "business":
            probability = 0.0
        elif payment_method == "upi" and error_reason == "timeout" and is_systemic_bucket:
            probability = 0.85
        elif error_reason == "gateway_error":
            probability = 0.90
        elif error_reason == "insufficient_funds":
            probability = 0.60
        elif error_reason == "card_expired":
            probability = 0.70
        elif error_reason == "authentication_failed":
            probability = 0.40
        elif error_reason == "incorrect_pin":
            probability = 0.30
        elif error_reason == "mandate_revoked":
            probability = 0.20
        else:
            probability = 0.55 if is_systemic_bucket else 0.35

        is_recoverable = random.random() < probability
        method_by_reason = {
            "payment_failed": "smart_retry",
            "gateway_error": "smart_retry",
            "server_error": "smart_retry",
            "timeout": "smart_retry",
            "insufficient_funds": "nudge",
            "card_expired": "payment_link",
            "authentication_failed": "nudge",
            "incorrect_pin": "nudge",
            "mandate_revoked": "payment_link",
        }
        difficulty = "easy" if probability >= 0.80 else "medium" if probability >= 0.50 else "hard"

        return {
            "is_recoverable": is_recoverable,
            "expected_recovery_method": method_by_reason.get(error_reason, "none")
            if is_recoverable
            else "none",
            "recovery_difficulty": difficulty,
        }

    def _scenario_for_bucket(self, bucket: str) -> tuple[str, tuple[str, str, str, str, str], bool]:
        if bucket == "systemic":
            return EventType.PAYMENT_FAILED.value, random.choice(self.SYSTEMIC_FAILURES), True
        if bucket == "customer":
            return EventType.PAYMENT_FAILED.value, random.choice(self.CUSTOMER_FAILURES), False
        if bucket == "subscription":
            event_type = random.choice(
                [EventType.SUBSCRIPTION_HALTED.value, EventType.SUBSCRIPTION_PENDING.value]
            )
            return event_type, random.choice(self.SUBSCRIPTION_FAILURES), False

        event_type = random.choice(
            [
                EventType.INVOICE_EXPIRED.value,
                EventType.INVOICE_OVERDUE.value,
                EventType.CHECKOUT_ABANDONED.value,
            ]
        )
        return event_type, random.choice(self.INVOICE_CHECKOUT_FAILURES), False

    def generate_batch(self) -> list[dict]:
        counts = {
            "systemic": int(self.num_events * 0.40),
            "customer": int(self.num_events * 0.25),
            "subscription": int(self.num_events * 0.20),
        }
        counts["invoice_checkout"] = self.num_events - sum(counts.values())

        events = []
        for bucket, count in counts.items():
            for _ in range(count):
                event_type, scenario, is_systemic_bucket = self._scenario_for_bucket(bucket)
                error_source, error_step, error_reason, error_code, error_description = scenario
                amount_paise = self._generate_amount_paise()
                payment_method = self._weighted_choice(self.PAYMENT_METHODS)
                bank_name = self._weighted_choice(self.BANKS)
                customer = self._generate_customer(payment_method)

                if error_reason == "timeout":
                    payment_method = "upi"
                    customer["upi_id"] = customer["upi_id"] or (
                        f"{customer['name'].lower().replace(' ', '.')}@ybl"
                    )

                metadata = {
                    "payment_method": payment_method,
                    "card_network": self._weighted_choice(self.CARD_NETWORKS)
                    if payment_method == "card"
                    else None,
                    "bank_name": bank_name,
                }

                events.append(
                    {
                        "event_id": str(uuid4()),
                        "event_type": event_type,
                        "razorpay_payment_id": f"pay_{self._id_suffix(14)}",
                        "razorpay_order_id": f"order_{self._id_suffix(14)}",
                        "amount_paise": amount_paise,
                        "currency": "INR",
                        "error_source": error_source,
                        "error_step": error_step,
                        "error_reason": error_reason,
                        "error_code": error_code,
                        "error_description": error_description,
                        "customer": customer,
                        "merchant_id": f"merch_{self._id_suffix(10).lower()}",
                        "timestamp": self._generate_timestamp(),
                        "metadata": metadata,
                        "ground_truth": self._ground_truth(
                            error_source,
                            error_reason,
                            payment_method,
                            is_systemic_bucket,
                            customer["opted_out"],
                        ),
                    }
                )

        random.shuffle(events)
        return events

    def save_batch(self, filepath: str) -> None:
        events = self.generate_batch()
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)

    def generate_for_training(self) -> tuple[list[dict], list[dict]]:
        original_num_events = self.num_events
        self.num_events = 2000
        events = self.generate_batch()
        self.num_events = original_num_events
        split_at = int(len(events) * 0.8)
        return events[:split_at], events[split_at:]
