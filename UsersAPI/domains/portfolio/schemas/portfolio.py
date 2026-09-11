from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


PaymentStatus = Literal["APLICADO", "ANULADO"]


class CreditLimitUpdate(BaseModel):
    approved_limit: Decimal = Field(ge=0, max_digits=18, decimal_places=2)


class CreditLimitRead(BaseModel):
    id: UUID
    tenant_id: int
    client_id: UUID
    approved_limit: Decimal
    credit_used: Decimal
    credit_available: Decimal
    active: bool
    created_at: datetime
    created_by: str
    updated_at: datetime | None
    updated_by: str | None

    model_config = {"from_attributes": True}


class ObligationRead(BaseModel):
    id: UUID
    tenant_id: int
    client_id: UUID
    sale_id: UUID
    sale_number: str | None = None
    business_date: date
    initial_amount: Decimal
    balance: Decimal
    status: str
    created_at: datetime
    created_by: str
    updated_at: datetime | None
    updated_by: str | None

    model_config = {"from_attributes": True}


class PaymentAllocationCreate(BaseModel):
    obligation_id: UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class PaymentCreate(BaseModel):
    client_id: UUID
    payment_date: date | None = None
    payment_method: str = Field(min_length=1, max_length=30)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
    allocations: list[PaymentAllocationCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_allocations(self):
        ids = [allocation.obligation_id for allocation in self.allocations]
        if len(ids) != len(set(ids)):
            raise ValueError("An obligation cannot be repeated in a payment")
        return self


class PaymentAllocationRead(BaseModel):
    id: UUID
    tenant_id: int
    payment_id: UUID
    obligation_id: UUID
    amount: Decimal

    model_config = {"from_attributes": True}


class PaymentRead(BaseModel):
    id: UUID
    tenant_id: int
    client_id: UUID
    payment_date: date
    business_date: date
    payment_method: str
    amount: Decimal
    status: PaymentStatus
    reference: str | None
    notes: str | None
    created_at: datetime
    created_by: str
    allocations: list[PaymentAllocationRead]

    model_config = {"from_attributes": True}
