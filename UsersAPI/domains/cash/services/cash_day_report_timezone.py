from datetime import timezone
from zoneinfo import ZoneInfo

from . import cash_day_report_service as report_service

COLOMBIA_TZ = ZoneInfo("America/Bogota")
UTC = timezone.utc


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


# The legacy report module keeps the calculations/renderers in one place.
# We replace only its timestamp helpers so PDF and Excel use the same rules.
report_service._to_colombia_datetime = _to_colombia_datetime
report_service._fmt_dt = _fmt_dt


def build_day_report(*args, **kwargs):
    return report_service.build_day_report(*args, **kwargs)


def excel_report(report):
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
    original_fmt = report_service._fmt_dt
    original_to_colombia = report_service._to_colombia_datetime
    report_service._fmt_dt = _fmt_dt
    report_service._to_colombia_datetime = _to_colombia_datetime
    try:
        return report_service.pdf_report(report)
    finally:
        report_service._fmt_dt = original_fmt
        report_service._to_colombia_datetime = original_to_colombia
