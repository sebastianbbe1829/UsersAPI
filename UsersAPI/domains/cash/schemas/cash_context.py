from datetime import date

from pydantic import BaseModel


class CashContextRead(BaseModel):
    assigned: bool
    tenant_id: int
    branch_id: int | None
    branch_name: str | None
    cash_box_id: int | None
    cash_box_name: str | None
    cash_box_status: str | None
    register_id: int | None
    register_status: str | None
    business_date: date | None
    day_id: int | None = None
    day_status: str | None = None
    branch_day_status: str | None = None
    operational: bool = False
    blocked_reason: str | None = None
