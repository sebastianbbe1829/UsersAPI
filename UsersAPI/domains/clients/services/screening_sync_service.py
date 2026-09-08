from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID

from UsersAPI.database import SessionLocal

from ..models import ScreeningSyncExecutionDB
from .screening_provider import sync_all_screening_lists


def create_sync_execution(
    db,
    trigger_type: str,
    triggered_by: int | None = None,
    triggered_by_email: str | None = None,
) -> ScreeningSyncExecutionDB:
    running = (
        db.query(ScreeningSyncExecutionDB)
        .filter(ScreeningSyncExecutionDB.status.in_(["PENDING", "RUNNING"]))
        .first()
    )
    if running is not None:
        return running

    execution = ScreeningSyncExecutionDB(
        trigger_type=trigger_type,
        triggered_by=triggered_by,
        triggered_by_email=triggered_by_email,
        status="PENDING",
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def run_sync_execution(execution_id: UUID) -> None:
    db = SessionLocal()
    started = datetime.now(UTC)
    started_perf = perf_counter()
    execution = None
    try:
        execution = db.get(ScreeningSyncExecutionDB, execution_id)
        if execution is None:
            return

        execution.status = "RUNNING"
        execution.started_at = started
        execution.error_message = None
        db.commit()

        result = sync_all_screening_lists(db)
        finished = datetime.now(UTC)
        execution.status = result["status"]
        execution.finished_at = finished
        execution.duration_ms = max(0, int((perf_counter() - started_perf) * 1000))
        execution.total_sources = result.get("total_sources")
        execution.successful_sources = result.get("successful_sources")
        execution.failed_sources = result.get("failed_sources")
        execution.result = result
        execution.error_message = None
        db.commit()
    except Exception as exc:
        db.rollback()
        if execution is None:
            execution = db.get(ScreeningSyncExecutionDB, execution_id)
        if execution is not None:
            execution.status = "ERROR"
            execution.finished_at = datetime.now(UTC)
            execution.duration_ms = max(0, int((perf_counter() - started_perf) * 1000))
            execution.error_message = str(exc)[:2000]
            db.commit()
    finally:
        db.close()


def list_sync_executions(db, limit: int = 50) -> list[ScreeningSyncExecutionDB]:
    return (
        db.query(ScreeningSyncExecutionDB)
        .order_by(ScreeningSyncExecutionDB.created_at.desc())
        .limit(limit)
        .all()
    )
