"""MABWiser-backed communication channel node."""

from backend.agents.common import append_audit, customer_from_case, enum_value
from backend.agents.state import RecoveryState
from backend.ml.channel_bandit import ChannelBandit
from backend.models.enums import ActionType


_bandit = ChannelBandit()
_NUDGE_ACTIONS = {
    ActionType.NUDGE_EMAIL.value,
    ActionType.NUDGE_SMS.value,
    ActionType.NUDGE_WHATSAPP.value,
}
_ACTION_BY_CHANNEL = {
    "email": ActionType.NUDGE_EMAIL.value,
    "sms": ActionType.NUDGE_SMS.value,
    "whatsapp": ActionType.NUDGE_WHATSAPP.value,
}


async def select_channel(state: RecoveryState) -> dict:
    strategy = dict(state.get("strategy") or {})
    action = enum_value(strategy.get("action_type"))
    if action not in _NUDGE_ACTIONS:
        return {"strategy": strategy, "selected_channel": strategy.get("channel")}

    customer = customer_from_case(state.get("case_data", {}))
    eligible = _eligible_channels(customer)
    if not eligible:
        strategy.update(
            {
                "action_type": ActionType.STOP.value,
                "channel": None,
                "reasoning": "No eligible customer communication channel is available.",
                "stopping_reason": "No eligible channel",
            }
        )
        audit = append_audit(
            state,
            "channel_bandit",
            "select_channel",
            "eligible_channels=[]",
            "action=stop",
            strategy["reasoning"],
        )
        return {"strategy": strategy, "selected_channel": None, "audit_trail": audit}

    segment = _bandit.segment_customer(customer)
    channel = _bandit.select_channel(segment, eligible)
    strategy["channel"] = channel
    strategy["action_type"] = _ACTION_BY_CHANNEL[channel]
    audit = append_audit(
        state,
        "channel_bandit",
        "select_channel",
        f"segment={segment}, eligible_channels={eligible}",
        f"selected_channel={channel}",
        "Thompson Sampling selection among eligible channels.",
    )
    return {"strategy": strategy, "selected_channel": channel, "audit_trail": audit}


def _eligible_channels(customer: dict) -> list[str]:
    if customer.get("opted_out", False):
        return []

    channels = []
    if customer.get("phone"):
        channels.append("sms")
    if customer.get("email"):
        channels.append("email")
    whatsapp_eligible = customer.get("whatsapp_eligible")
    if customer.get("phone") and whatsapp_eligible is not False:
        channels.append("whatsapp")
    return channels
