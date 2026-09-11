from copy import copy
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

from reportlab.lib.units import mm
from reportlab.platypus import Spacer
from sqlalchemy import select

from UsersAPI.domains.sales.models import SaleDB, SalePaymentDB

from ..models import CashMovementDB
from . import cash_day_report_service as report_service

COLOMBIA_TZ = ZoneInfo("America/Bogota")
UTC = timezone.utc
LEGACY_LOCAL_OFFSET = timedelta(hours=5)
_CURRENT_REPORT = None


def _to_colombia_datetime(value):
    """Interpret stored naive Caja timestamps as UTC and render them in Colombia."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(COLOMBIA_TZ)


def _fmt_dt(value, empty="—"):
    """Render Caja timestamps in Colombian 24-hour format."""
    value = _to_colombia_datetime(value)
    return value.strftime("%d/%m/%Y %H:%M:%S") if value else empty


def _normalize_legacy_report_timestamps(report):
    """Correct legacy local-naive close timestamps without changing persisted data."""
    day = report.get("day")
    if day is not None and day.opened_at and day.closed_at and day.closed_at < day.opened_at:
        report["day"] = copy(day)
        report["day"].closed_at = day.closed_at + LEGACY_LOCAL_OFFSET

    for row in report.get("registers", []):
        opened_at = row.get("opened_at")
        closed_at = row.get("closed_at")
        if opened_at and closed_at and closed_at < opened_at:
            row["closed_at"] = closed_at + LEGACY_LOCAL_OFFSET


def _assign_credit_sales_to_registers(report, db, tenant_id):
    """Associate credit sales with their sale register without creating cash movement."""
    day = report.get("day")
    if day is None:
        return

    movements = db.scalars(
        select(CashMovementDB).where(
            CashMovementDB.tenant_id == tenant_id,
            CashMovementDB.business_date == day.business_date,
            CashMovementDB.origin_type == "SALE",
        )
    ).all()

    sale_register = {}
    for movement in movements:
        sale_register.setdefault(str(movement.origin_id), movement.cash_register_id)

    register_rows = {row["register_id"]: row for row in report["registers"]}
    credit_total = report_service._money(report["sales_day"].get("Crédito", report_service.ZERO))
    unassigned_credit = credit_total
