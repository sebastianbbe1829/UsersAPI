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

    credit_rows = db.execute(
        select(SalePaymentDB.sale_id, SalePaymentDB.amount, SalePaymentDB.cash_register_id)
        .join(SaleDB, SaleDB.id == SalePaymentDB.sale_id)
        .where(
            SalePaymentDB.tenant_id == tenant_id,
            SaleDB.tenant_id == tenant_id,
            SaleDB.business_date == day.business_date,
            SaleDB.status != "CANCELLED",
            SalePaymentDB.payment_method.in_(["CREDITO", "CREDIT", "CRÉDITO"]),
        )
    ).all()

    unmapped_rows = []
    for sale_id, amount, stored_register_id in credit_rows:
        value = report_service._money(amount)
        register_id = stored_register_id or sale_register.get(str(sale_id))
        if register_id is None or register_id not in register_rows:
            unmapped_rows.append(value)
            continue

        row = register_rows[register_id]
        row["sales"]["Crédito"] = row["sales"].get("Crédito", report_service.ZERO) + value
        report["sales_by_box_totals"]["Crédito"] = (
            report["sales_by_box_totals"].get("Crédito", report_service.ZERO) + value
        )
        unassigned_credit -= value

    report["unassigned_credit_sales"] = max(
        report_service.ZERO,
        report_service._money(unassigned_credit),
    )


def _without_sales_difference_paragraph(text, style, *args, **kwargs):
    """Hide technical reconciliation text and show only unassigned credit sales."""
    if isinstance(text, str) and text.startswith(
        "Diferencia entre ventas del día y ventas asignadas a cajas:"
    ):
        return Spacer(1, 0)

    if isinstance(text, str) and text.startswith("Ventas a crédito del día"):
        unassigned = (
            _CURRENT_REPORT.get("unassigned_credit_sales", report_service.ZERO)
            if _CURRENT_REPORT is not None
            else report_service.ZERO
        )
        if not unassigned:
            return Spacer(1, 0)
        text = (
            "Ventas a crédito del día (sin movimiento de caja asignable): "
            f"{report_service._money_text(unassigned)}"
        )

    return _ORIGINAL_PARAGRAPH(text, style, *args, **kwargs)


report_service._to_colombia_datetime = _to_colombia_datetime
report_service._fmt_dt = _fmt_dt
_ORIGINAL_PARAGRAPH = report_service.Paragraph
_ORIGINAL_SPACER = report_service.Spacer
_ORIGINAL_DOC = report_service.SimpleDocTemplate


def build_day_report(*args, **kwargs):
    report = report_service.build_day_report(*args, **kwargs)
    _normalize_legacy_report_timestamps(report)
    db = args[0] if args else kwargs["db"]
    tenant_id = args[1] if len(args) > 1 else kwargs["tenant_id"]
    _assign_credit_sales_to_registers(report, db, tenant_id)
    return report


def excel_report(report):
    _normalize_legacy_report_timestamps(report)
    original_fmt = report_service._fmt_dt
    original_to_colombia = report_service._to_colombia_datetime
    report_service._fmt_dt = _fmt_dt
    report_service._to_colombia_datetime = _to_colombia_datetime
    try:
        return report_service.excel_report(report)
    finally:
        report_service._fmt_dt = original_fmt
        report_service._to_colombia_datetime = original_to_colombia


def _compact_doc(*args, **kwargs):
    """Use the available landscape A4 height more efficiently so the report fits one page."""
    kwargs.update(
        {
            "rightMargin": 6 * mm,
            "leftMargin": 6 * mm,
            "topMargin": 5 * mm,
            "bottomMargin": 5 * mm,
        }
    )
    return _ORIGINAL_DOC(*args, **kwargs)


def _compact_spacer(width, height):
    # The report contains several section spacers. Keep visual separation while
    # avoiding unnecessary page breaks in the one-page daily closing report.
    return _ORIGINAL_SPACER(width, min(height, 2 * mm))


def pdf_report(report):
    global _CURRENT_REPORT
    _normalize_legacy_report_timestamps(report)
    original_fmt = report_service._fmt_dt
    original_to_colombia = report_service._to_colombia_datetime
    original_paragraph = report_service.Paragraph
    original_doc = report_service.SimpleDocTemplate
    original_spacer = report_service.Spacer
    report_service._fmt_dt = _fmt_dt
    report_service._to_colombia_datetime = _to_colombia_datetime
    report_service.Paragraph = _without_sales_difference_paragraph
    report_service.SimpleDocTemplate = _compact_doc
    report_service.Spacer = _compact_spacer
    _CURRENT_REPORT = report
    try:
        return report_service.pdf_report(report)
    finally:
        _CURRENT_REPORT = None
        report_service._fmt_dt = original_fmt
        report_service._to_colombia_datetime = original_to_colombia
        report_service.Paragraph = original_paragraph
        report_service.SimpleDocTemplate = original_doc
        report_service.Spacer = original_spacer
