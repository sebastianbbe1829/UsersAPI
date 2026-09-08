from __future__ import annotations

from datetime import UTC, datetime
import logging
from time import perf_counter
from uuid import UUID

from UsersAPI.database import SessionLocal

from ..models import ScreeningSyncExecutionDB
from .screening_bulk_sync_service import sync_all_screening_lists_bulk


logger = logging.getLogger("UsersAPI.screening")


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
        logger.warning(
            "[SCREENING_SYNC] Se solicitó una nueva ejecución %s pero ya existe "
            "una activa id=%s status=%s",
            trigger_type,
            running.id,
            running.status,
        )
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
    logger.info(
        "[SCREENING_SYNC] Ejecución creada id=%s origen=%s usuario=%s status=PENDING",
        execution.id,
        trigger_type,
        triggered_by_email or "-",
    )
    return execution


def run_sync_execution(execution_id: UUID) -> None:
    db = SessionLocal()
    started = datetime.now(UTC)
    started_perf = perf_counter()
    execution = None
    logger.info("[SCREENING_SYNC] Background task iniciada id=%s", execution_id)
    try:
        execution = db.get(ScreeningSyncExecutionDB, execution_id)
        if execution is None:
            logger.error("[SCREENING_SYNC] No existe ejecución id=%s", execution_id)
            return

        execution.status = "RUNNING"
        execution.started_at = started
        execution.error_message = None
        db.commit()
        logger.info(
            "[SCREENING_SYNC] Ejecución id=%s RUNNING desde %s",
            execution_id,
            started.isoformat(),
        )

        result = sync_all_screening_lists_bulk(db)
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
        logger.info(
            "[SCREENING_SYNC] Ejecución id=%s FINALIZADA status=%s duración_ms=%s fuentes=%s/%s",
            execution_id,
            execution.status,
            execution.duration_ms,
            execution.successful_sources,
            execution.total_sources,
        )
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
        logger.exception(
            "[SCREENING_SYNC] Ejecución id=%s terminó con ERROR: %s",
            execution_id,
            exc,
        )
    finally:
        db.close()
        logger.info("[SCREENING_SYNC] Background task finalizada id=%s", execution_id)


def list_sync_executions(db, limit: int = 50) -> list[ScreeningSyncExecutionDB]:
    return (
        db.query(ScreeningSyncExecutionDB)
        .order_by(ScreeningSyncExecutionDB.created_at.desc())
        .limit(limit)
        .all()
    )
