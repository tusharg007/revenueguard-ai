"""Small helpers shared by recovery graph nodes."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.agents.state import RecoveryState


def enum_value(value: Any) -> str:
    return str(getattr(value, "value", value or "")).lower()


def customer_from_case(case: dict) -> dict:
    customer = case.get("customer") or case.get("customer_data") or {}
    return customer if isinstance(customer, dict) else {}


def metadata_from_case(case: dict) -> dict:
    metadata = case.get("metadata") or {}
    return metadata if isinstance(metadata, dict) else {}


def case_value(case: dict, *names: str, default: Any = "") -> Any:
    for name in names:
        value = case.get(name)
        if value is not None:
            return getattr(value, "value", value)
    return default


def append_audit(
    state: RecoveryState,
    agent_name: str,
    step: str,
    input_summary: str,
    output_summary: str,
    reasoning: str = "",
    guardrails: list[str] | None = None,
) -> list[dict]:
    entry = {
        "id": str(uuid4()),
        "case_id": state.get("case_id", ""),
        "action_id": None,
        "agent_name": agent_name,
        "step": step,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "reasoning": reasoning,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "guardrails_applied": guardrails or [],
        "duration_ms": 0,
    }
    return [*state.get("audit_trail", []), entry]


def response_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
        return "".join(parts)
    return str(content)


def parse_json_response(response: Any) -> dict:
    text = response_text(response).strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("LLM response did not contain a JSON object") from None
        try:
            payload = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError("LLM returned invalid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("LLM response must be a JSON object")
    return payload
