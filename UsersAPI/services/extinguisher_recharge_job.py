import asyncio
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text

from ..database import BootstrapSessionLocal
from ..logging_config import logger
from .extinguisher_recharge_notification_service import ExtinguisherRechargeNotificationService


TIMEZONE = os.getenv("JOB_TIMEZONE", "America/Bogota")
RUN_TIME = os.getenv("EXTINGUISHER_RECHARGE_NOTIFICATION_TIME", "07:00")
ENABLED = os.getenv("EXTINGUISHER_RECHARGE_NOTIFICATIONS_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
ADVISORY_LOCK_ID = 824731905


def _scheduled_target(now: datetime) -> datetime:
    hour, minute = [int(value) for value in RUN_TIME.split(":", 1)]
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _next_run(now: datetime) -> datetime:
    target = _scheduled_target(now)
    if target <= now:
        target += timedelta(days=1)
    return target


def run_extinguisher_recharge_notification_job(*, wait_for_schedule: bool = False) -> dict:
    """Ejecuta el job, opcionalmente respetando la hora configurada en JOB_TIMEZONE."""
    if wait_for_schedule:
        timezone = ZoneInfo(TIMEZONE)
        now = datetime.now(timezone)
        target = _scheduled_target(now)
        if now < target:
            delay = (target - now).total_seconds()
            logger.info(
                "Extinguisher recharge notification triggered before configured time; "
                "waiting %.0f seconds until %s (%s)",
                delay,
                RUN_TIME,
                TIMEZONE,
            )
            import time
            time.sleep(delay)
        else:
            logger.info(
                "Extinguisher recharge notification triggered at/after configured time "
                "(%s %s); executing now",
                RUN_TIME,
                TIMEZONE,
            )

    db = BootstrapSessionLocal()
    locked = False
    try:
        locked = bool(
            db.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": ADVISORY_LOCK_ID},
            ).scalar()
        )

        if not locked:
            return {
                "status": "skipped",
                "reason": "another_instance_is_running",
            }

        result = ExtinguisherRechargeNotificationService(db).run()
        logger.info("Daily extinguisher recharge notification result: %s", result)
        return result
    finally:
        if locked:
            try:
                db.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": ADVISORY_LOCK_ID},
                )
            except Exception:
                logger.exception("Could not release recharge notification advisory lock")
        db.close()


async def _run_once() -> None:
    try:
        run_extinguisher_recharge_notification_job()
    except Exception:
        logger.exception("Daily extinguisher recharge notification failed")


async def daily_extinguisher_recharge_job(stop_event: asyncio.Event) -> None:
    if not ENABLED:
        logger.info("Daily extinguisher recharge notifications are disabled")
        return

    timezone = ZoneInfo(TIMEZONE)
    logger.info("Daily extinguisher recharge job configured for %s (%s)", RUN_TIME, TIMEZONE)

    while not stop_event.is_set():
        now = datetime.now(timezone)
        target = _next_run(now)
        delay = max((target - now).total_seconds(), 1)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=delay)
            continue
        except asyncio.TimeoutError:
            await _run_once()
