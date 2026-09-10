from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CashDayBranchRead(BaseModel):
    id: int
    branch_id: int
    branch_name: str
    status: str
    opened_at: datetime
    closed_at: datetime | None = None
    closed_by: str | None = None


class CashDayRegisterRead(BaseModel):
    id: int
    branch_id: int | None
    branch_name: str | None
    cash_box_id: int | None
    cash_box_name: str | None
    status: str
    opening_amount: Decimal
    expected_cash: Decimal | None = None
    counted_cash: Decimal | None = None
    difference: Decimal | None = None
    closed_at: datetime | None = None
    closed_by: str | None = None


class CashDayRead(BaseModel):
    id: int
    tenant_id: int
    business_date: date
    status: str
    opened_at: datetime
    opened_by: str
    closed_at: datetime | None = None
    closed_by: str | None = None
    closing_notes: str | None = None
    branches: list[CashDayBranchRead] = []
    registers: list[CashDayRegisterRead] = []


class CashDayStart(BaseModel):
    business_date: date = Field(description="Fecha contable del día operativo; puede ser futura.")


class CashDayClose(BaseModel):
    closing_notes: str | None = None
