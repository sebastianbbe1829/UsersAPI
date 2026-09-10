from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CashRegisterOpen(BaseModel):
    opening_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=2)


class CashMovementCreate(BaseModel):
    movement_type: str = Field(min_length=1, max_length=20)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    description: str | None = Field(default=None, max_length=500)


class CashRegisterClose(BaseModel):
    counted_cash: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    closing_notes: str | None = Field(default=None, max_length=500)


class CashMovementRead(BaseModel):
    id: int
    cash_register_id: int
    movement_type: str
    amount: Decimal
    payment_method: str | None
    origin_type: str
    origin_id: str | None
    description: str | None
    created_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class CashRegisterSummary(BaseModel):
    sales_cash: Decimal
    sales_transfer: Decimal
    sales_card: Decimal
    sales_credit: Decimal
    portfolio_cash: Decimal
    manual_income: Decimal
    manual_expense: Decimal
    expected_cash: Decimal
    counted_cash: Decimal | None
    difference: Decimal | None


class CashRegisterRead(BaseModel):
    id: int
    tenant_id: int
    opened_at: datetime
    opened_by: str
    opening_amount: Decimal
    status: str
    closed_at: datetime | None
    closed_by: str | None
    expected_cash: Decimal | None
    counted_cash: Decimal | None
    difference: Decimal | None
    closing_notes: str | None
    created_at: datetime
    updated_at: datetime | None
    movements: list[CashMovementRead] = []
    summary: CashRegisterSummary | None = None

    model_config = {"from_attributes": True}
