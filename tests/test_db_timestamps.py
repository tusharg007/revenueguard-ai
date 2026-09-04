"""Regression checks for UTC timestamps on SQLite and PostgreSQL/asyncpg."""
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, select, text
from sqlalchemy.dialects.postgresql.asyncpg import dialect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.db.database import Base
from backend.db.orm_models import Experiment, RecoveryApproval, RecoveryCase
from backend.db.types import UTCDateTime

IST = timezone(timedelta(hours=5, minutes=30))
UTC_VALUE = datetime(2026, 9, 4, 17, 0, tzinfo=timezone.utc)


class TimestampTests(unittest.TestCase):
    def test_every_timestamp_binds_as_naive_utc_for_asyncpg(self):
        columns = [
            column for table in Base.metadata.tables.values() for column in table.columns
            if isinstance(column.type, (DateTime, UTCDateTime))
        ]
        self.assertTrue(columns)
        for column in columns:
            with self.subTest(column=str(column)):
                self.assertIsInstance(column.type, UTCDateTime)
                column_type = column.type.dialect_impl(dialect())
                bind = column_type.bind_processor(dialect())
                for value in (UTC_VALUE, UTC_VALUE.astimezone(IST), UTC_VALUE.replace(tzinfo=None)):
                    self.assertEqual(bind(value), UTC_VALUE.replace(tzinfo=None))
                self.assertIsNone(bind(None))
                self.assertEqual(column_type.compile(dialect=dialect()), "TIMESTAMP WITHOUT TIME ZONE")

    def test_read_restores_utc_and_null(self):
        result = UTCDateTime().result_processor(dialect(), None)
        self.assertIsNone(result(None))
        for value in (UTC_VALUE, UTC_VALUE.astimezone(IST), UTC_VALUE.replace(tzinfo=None)):
            self.assertEqual(result(value), UTC_VALUE)
            self.assertEqual(result(value).tzinfo, timezone.utc)


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_startup_seeds_default_experiment_idempotently(self):
        from backend.api.main import _create_default_experiment
        async with self.sessions() as session:
            await _create_default_experiment(session)
            await session.commit()
            await _create_default_experiment(session)
            await session.commit()
        async with self.sessions() as session:
            experiments = (await session.scalars(select(Experiment))).all()
            self.assertEqual(len(experiments), 1)
            self.assertEqual(experiments[0].started_at.tzinfo, timezone.utc)

    async def test_case_and_approval_timestamps_round_trip(self):
        async with self.sessions() as session:
            session.add(RecoveryCase(
                case_id="test-case", event_type="payment.failed", external_payment_id="pay_test",
                amount_paise=50000, failure_category="SYSTEMIC", failure_source="bank",
                customer_id="test-customer", customer_data={}, merchant_id="test-merchant",
                created_at=UTC_VALUE.astimezone(IST),
            ))
            await session.flush()
            session.add(RecoveryApproval(
                approval_id="test-approval", case_id="test-case", payment_id="pay_test",
                amount_paise=50000, requested_action="smart_retry",
                expires_at=UTC_VALUE.astimezone(IST) + timedelta(hours=24),
            ))
            await session.commit()
        async with self.sessions() as session:
            case = await session.scalar(select(RecoveryCase))
            approval = await session.scalar(select(RecoveryApproval))
            self.assertEqual(case.created_at, UTC_VALUE)
            self.assertIsNone(case.last_retry_at)
            self.assertGreater(approval.expires_at, case.created_at)
            case.last_retry_at = UTC_VALUE.astimezone(IST)
            approval.approved_at = UTC_VALUE
            await session.commit()
        async with self.sessions() as session:
            case = await session.scalar(select(RecoveryCase))
            approval = await session.scalar(select(RecoveryApproval))
            self.assertEqual(case.last_retry_at, UTC_VALUE)
            self.assertEqual(case.updated_at.tzinfo, timezone.utc)
            self.assertEqual(approval.approved_at, UTC_VALUE)
            raw = await session.scalar(text("SELECT created_at FROM recovery_cases"))
            self.assertEqual(raw, "2026-09-04 17:00:00.000000")


if __name__ == "__main__":
    unittest.main()

