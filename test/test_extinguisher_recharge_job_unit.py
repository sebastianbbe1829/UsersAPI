import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from UsersAPI.services import extinguisher_recharge_job as job


def test_scheduled_target_and_next_run():
    now = datetime(2026, 9, 3, 8, 30, 45)
    assert job._scheduled_target(now) == datetime(2026, 9, 3, 7, 0, 0)
    assert job._next_run(now) == datetime(2026, 9, 4, 7, 0, 0)


def test_next_run_before_configured_time():
    now = datetime(2026, 9, 3, 6, 30)
    assert job._next_run(now) == datetime(2026, 9, 3, 7, 0)


def test_run_disabled(monkeypatch):
    monkeypatch.setattr(job, "ENABLED", False)
    assert job.run_extinguisher_recharge_notification_job() == {
        "status": "skipped",
        "reason": "notifications_disabled",
    }


def test_run_before_configured_time(monkeypatch):
    class FakeDateTime:
        @classmethod
        def now(cls, timezone):
            return datetime(2026, 9, 3, 6, 0, tzinfo=timezone)

    monkeypatch.setattr(job, "datetime", FakeDateTime)
    monkeypatch.setattr(job, "ENABLED", True)
    monkeypatch.setattr(job, "RUN_TIME", "07:00")
    result = job.run_extinguisher_recharge_notification_job()
    assert result["status"] == "skipped"
    assert result["reason"] == "before_configured_time"
    assert result["configured_time"] == "07:00"


def test_run_skips_when_advisory_lock_is_not_acquired(monkeypatch):
    db = MagicMock()
    db.execute.return_value.scalar.return_value = False
    session_factory = MagicMock(return_value=db)
    monkeypatch.setattr(job, "BootstrapSessionLocal", session_factory)
    monkeypatch.setattr(job, "ENABLED", True)

    class FakeDateTime:
        @classmethod
        def now(cls, timezone):
            return datetime(2026, 9, 3, 8, 0, tzinfo=timezone)

    monkeypatch.setattr(job, "datetime", FakeDateTime)
    result = job.run_extinguisher_recharge_notification_job()
    assert result == {
        "status": "skipped",
        "reason": "another_instance_is_running",
    }
    db.close.assert_called_once()


def test_run_executes_service_and_unlocks(monkeypatch):
    db = MagicMock()
    db.execute.return_value.scalar.side_effect = [True, None]
    service = MagicMock()
    service.run.return_value = {"emails_sent": 2}
    monkeypatch.setattr(job, "BootstrapSessionLocal", lambda: db)
    monkeypatch.setattr(job, "ExtinguisherRechargeNotificationService", lambda value: service)
    monkeypatch.setattr(job, "ENABLED", True)

    class FakeDateTime:
        @classmethod
        def now(cls, timezone):
            return datetime(2026, 9, 3, 8, 0, tzinfo=timezone)

    monkeypatch.setattr(job, "datetime", FakeDateTime)
    assert job.run_extinguisher_recharge_notification_job() == {"emails_sent": 2}
    service.run.assert_called_once_with()
    assert db.execute.call_count == 2
    db.close.assert_called_once()


def test_run_unlock_error_is_logged_and_db_closes(monkeypatch):
    db = MagicMock()
    db.execute.side_effect = [SimpleNamespace(scalar=lambda: True), RuntimeError("unlock")]
    monkeypatch.setattr(job, "BootstrapSessionLocal", lambda: db)
    service = MagicMock()
    service.run.return_value = {"ok": True}
    monkeypatch.setattr(job, "ExtinguisherRechargeNotificationService", lambda value: service)
    monkeypatch.setattr(job, "ENABLED", True)

    class FakeDateTime:
        @classmethod
        def now(cls, timezone):
            return datetime(2026, 9, 3, 8, 0, tzinfo=timezone)

    monkeypatch.setattr(job, "datetime", FakeDateTime)
    assert job.run_extinguisher_recharge_notification_job() == {"ok": True}
    db.close.assert_called_once()


def test_run_once_swallows_job_error(monkeypatch):
    runner = MagicMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(job, "run_extinguisher_recharge_notification_job", runner)
    asyncio.run(job._run_once())
    runner.assert_called_once()


def test_daily_job_disabled(monkeypatch):
    monkeypatch.setattr(job, "ENABLED", False)
    asyncio.run(job.daily_extinguisher_recharge_job(asyncio.Event()))


def test_daily_job_runs_once_on_timeout(monkeypatch):
    async def scenario():
        stop_event = asyncio.Event()
        run_once = AsyncMock(side_effect=stop_event.set)
        monkeypatch.setattr(job, "_run_once", run_once)
        monkeypatch.setattr(job, "ENABLED", True)
        monkeypatch.setattr(job, "_next_run", lambda now: now)

        await job.daily_extinguisher_recharge_job(stop_event)
        run_once.assert_awaited_once()

    asyncio.run(scenario())
