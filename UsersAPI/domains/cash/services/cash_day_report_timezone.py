from copy import copy
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

from reportlab.platypus import Spacer

from . import cash_day_report_service as report_service

COLOMBIA_TZ = ZoneInfo("America/Bogota")
UTC = timezone.utc
LEGACY_LOCAL_OFFSET = timedelta(hours=5)


def _to_colombia_datetime(value):
    """Interpret stored naive Caja timestamps as UTC and render them in Colombia."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(COLOMBIA_TZ)


def _fmt_dt(value, empty="—"):
    """Render Caja timestamps in Colombian 12-hour format."""
    value = _to_colombia_datetime(value)
    return value.strftime("%d/%m/%Y %I:%M:%S %p") if value else empty


def _normalize_legacy_report_timestamps(report):
    """Correct legacy local-naive close timestamps without changing persisted data.

    Caja timestamps are now stored as UTC-naive values. Older close timestamps were
    sometimes persisted as Colombia local time. When that legacy value is earlier
    than its corresponding opening timestamp, the only valid interpretation for a
    same-day register is the legacy local value plus five hours before UTC rendering.
    """
    day = report.get("day")
    if day is not None and day.opened_at and day.closed_at and day.closed_at < day.opened_at:
        report["day"] = copy(day)
        report["day"].closed_at = day.closed_at + LEGACY_LOCAL_OFFSET

    for row in report.get("registers", []):
        opened_at = row.get("opened_at")
        closed_at = row.get("closed_at")
        if opened_at and closed_at and closed_at < opened_at:
            row["closed_at"] = closed_at + LEGACY_LOCAL_OFFSET


def _without_sales_difference_paragraph(text, style, *args, **kwargs):
    """Hide the technical sales reconciliation line from the PDF only."""
    if isinstance(text, str) and text.startswith(
        "Diferencia entre ventas del día y ventas asignadas a cajas:"
    ):
        return Spacer(1, 0)
    return _ORIGINAL_PARAGRAPH(text, style, *args, **kwargs)


# The legacy report module keeps the calculations/renderers in one place.
# We replace only its timestamp helpers so PDF and Excel use the same rules.
report_service._to_colombia_datetime = _to_colombia_datetime
report_service._fmt_dt = _fmt_dt
_ORIGINAL_PARAGRAPH = report_service.Paragraph


def build_day_report(*args, **kwargs):
    report = report_service.build_day_report(*args, **kwargs)
    _normalize_legacy_report_timestamps(report)
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


def pdf_report(report):
    _normalize_legacy_report_timestamps(report)
    original_fmt = report_service._fmt_dt
    original_to_colombia = report_service._to_colombia_datetime
    original_paragraph = report_service.Paragraph
    report_service._fmt_dt = _fmt_dt
    report_service._to_colombia_datetime = _to_colombia_datetime
    report_service.Paragraph = _without_sales_difference_paragraph
    try:
        return report_service.pdf_report(report)
    finally:
        report_service._fmt_dt = original_fmt
        report_service._to_colombia_datetime = original_to_colombia
        report_service.Paragraph = original_paragraph
