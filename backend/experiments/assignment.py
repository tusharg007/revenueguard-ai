"""Stable A/B experiment assignment helpers."""

from __future__ import annotations

import hashlib
import inspect
from collections.abc import Awaitable
from typing import Any, overload

from sqlalchemy import select

from backend.db.orm_models import ExperimentAssignmentRecord
from backend.models.enums import ExperimentArm


def assign_experiment_arm(
    case_id: str,
    experiment_id: str = "recovery_agent_v1",
    variant_pct: int = 20,
) -> ExperimentArm:
    """Return a deterministic arm so retries cannot switch treatment groups."""
    if not 0 <= variant_pct <= 100:
        raise ValueError("variant_pct must be between 0 and 100")

    bucket = int(
        hashlib.md5(f"{experiment_id}:{case_id}".encode("utf-8")).hexdigest(), 16
    ) % 100
    return ExperimentArm.TREATMENT if bucket < variant_pct else ExperimentArm.CONTROL


@overload
def get_existing_assignment(
    case_id: str, experiment_id: str, db_session: Any
) -> ExperimentArm | None: ...


@overload
def get_existing_assignment(
    case_id: str, experiment_id: str, db_session: Any
) -> Awaitable[ExperimentArm | None]: ...


def get_existing_assignment(
    case_id: str, experiment_id: str, db_session: Any
) -> ExperimentArm | None | Awaitable[ExperimentArm | None]:
    """Look up a persisted assignment with sync and async SQLAlchemy support.

    The application uses ``AsyncSession``. Supporting synchronous test sessions as
    well keeps this small helper convenient outside request handling.
    """
    statement = (
        select(ExperimentAssignmentRecord.arm)
        .where(ExperimentAssignmentRecord.case_id == case_id)
        .where(ExperimentAssignmentRecord.experiment_id == experiment_id)
        .order_by(ExperimentAssignmentRecord.assigned_at.desc())
        .limit(1)
    )
    result = db_session.execute(statement)

    if inspect.isawaitable(result):
        return _resolve_async_assignment(result)

    return _assignment_from_result(result)


async def _resolve_async_assignment(result_awaitable: Awaitable[Any]) -> ExperimentArm | None:
    return _assignment_from_result(await result_awaitable)


def _assignment_from_result(result: Any) -> ExperimentArm | None:
    arm = result.scalar_one_or_none()
    return ExperimentArm(arm) if arm is not None else None
