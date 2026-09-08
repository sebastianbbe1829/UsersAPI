from __future__ import annotations

import os
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text

from UsersAPI.database import SessionLocal
from UsersAPI.logging_config import logger

from ..models import ScreeningSyncExecutionDB
from .screening_sync_service import create_sync_execution, run_sync_execution


TIMEZONE = os.getenv("JOB_TIMEZONE", "America/Bogota")
RUN_TIME = os.getenv("RESTRICTIVE_LISTS_SYNC_TIME", "07:00")
ENABLED = (
    os.getenv("RESTRICTIVE_LISTS_SYNC_ENABLED", "true").lower()
    in {"1", "true", "yes", "on"}
)
ADVISORY_LOCK_ID = 824731906


def _scheduled_target(now: datetime) -> datetime:
    hour, minute = [int(value) for value in RUN_TIME.split(":", 1)]
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _utc_day_bounds(now: datetime) -> tuple[datetime, datetime]:
    timezone = ZoneInfo(TIMEZONE)
    local_start = datetime.combine(now.date(), time.min, tzinfo=timezone)
    local_end = local_start + timedelta(days=1)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)


def _already_succeeded_today(db, now: datetime) -> bool:
    start_utc, end_utc = _utc_day_bounds(now)
    execution = (
        db.query(ScreeningSyncExecutionDB)
        .filter(
            ScreeningSyncExecutionDB.status == "SUCCESS",
            ScreeningSyncExecutionDB.created_at >= start_utc,
            ScreeningSyncExecutionDB.created_at < end_utc,
        )
        .first()
    )
    return execution is not None


def run_restrictive_lists_sync_job(trigger_type: str = "MANUAL") -> dict:
    """Ejecuta la sincronización una sola vez por día y evita concurrencia."""
    if not ENABLED:
        logger.info("Restrictive lists synchronization is disabled")
        return {"status": "skipped", "reason": "sync_disabled"}

    timezone = ZoneInfo(TIMEZONE)
    now = datetime.now(timezone)
    target = _scheduled_target(now)

    if now < target:
        logger.info(
            "Restrictive lists sync triggered before configured time; skipping: "
            "current=%s configured=%s timezone=%s trigger=%s",
            now.strftime("%H:%M:%S"),
            RUN_TIME,
            TIMEZONE,
            trigger_type,
        )
        return {
            "status": "skipped",
            "reason": "before_configured_time",
            "current_time": now.strftime("%H:%M:%S"),
            "configured_time": RUN_TIME,
            "timezone": TIMEZONE,
            "trigger_type": trigger_type,
        }

    logger.info(
        "[SCREENING_SYNC_JOB] Trigger=%s current=%s configured=%s timezone=%s",
        trigger_type,
        now.strftime("%H:%M:%S"),
        RUN_TIME,
        TIMEZONE,
    )

    db = SessionLocal()
    locked = False
    try:
        locked = bool(
            db.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": ADVISORY_LOCK_ID},
            ).scalar()
        )
        if not locked:
            logger.warning("[SCREENING_SYNC_JOB] Another instance is already running")
            return {"status": "skipped", "reason": "another_instance_is_running"}

        if _already_succeeded_today(db, now):
            logger.info(
                "[SCREENING_SYNC_JOB] Ya existe una sincronización SUCCESS para %s; no se ejecuta nuevamente",
                now.date().isoformat(),
            )
            return {
                "status": "skipped",
                "reason": "already_succeeded_today",
                "execution_date": now.date().isoformat(),
            }

        execution = create_sync_execution(db, trigger_type=trigger_type)
        execution_id = execution.id
        logger.info(
            "[SCREENING_SYNC_JOB] Iniciando ejecución id=%s trigger=%s",
            execution_id,
            trigger_type,
        )

        run_sync_execution(execution_id)

        execution = db.get(ScreeningSyncExecutionDB, execution_id)
        if execution is None:
            raise RuntimeError(f"No se pudo recuperar la ejecución {execution_id}")

        result = {
            "status": execution.status,
            "execution_id": str(execution.id),
            "trigger_type": execution.trigger_type,
            "duration_ms": execution.duration_ms,
            "total_sources": execution.total_sources,
            "successful_sources": execution.successful_sources,
            "failed_sources": execution.failed_sources,
        }
        logger.info("[SCREENING_SYNC_JOB] Resultado: %s", result)
        return result
    finally:
        if locked:
            try:
                db.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": ADVISORY_LOCK_ID},
                )
            except Exception:
                logger.exception("[SCREENING_SYNC_JOB] Could not release advisory lock")
        db.close()
