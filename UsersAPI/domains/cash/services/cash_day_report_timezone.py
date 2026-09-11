from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from . import cash_day_report_service as report_service

COLOMBIA_TZ = ZoneInfo("America/Bogota")
UTC = timezone.utc


def _to_colombia_datetime(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(COLOMBIA_TZ)


def _fmt_dt(value, empty="—"):
    value = _to_colombia_datetime(value)
    return value.strftime("%d/%m/%Y %I:%M:%S %p") if value else empty


def _configure_report_timezone():
    report_service._to_colombia_datetime = _to_colombia_datetime
    report_service._fmt_dt = _fmt_dt


def build_day_report(*args, **kwargs):
    _configure_report_timezone()
    return report_service.build_day_report(*args, **kwargs)


def excel_report(report):
    _configure_report_timezone()
    return report_service.excel_report(report)


def pdf_report(report):
    _configure_report_timezone()
    return report_service.pdf_report(report)
