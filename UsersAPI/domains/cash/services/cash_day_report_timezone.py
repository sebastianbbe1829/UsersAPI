from datetime import timezone
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


report_service._to_colombia_datetime = _to_colombia_datetime
report_service._fmt_dt = _fmt_dt

build_day_report = report_service.build_day_report
excel_report = report_service.excel_report
pdf_report = report_service.pdf_report
