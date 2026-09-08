from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class SaleItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=3)


class SaleCustomerCreate(BaseModel):
    client_id: UUID | None = None
    allocation_percentage: Decimal = Field(gt=0, le=100, max_digits=7, decimal_places=4)
    is_generic: bool = False


class SalePaymentCreate(BaseModel):
    payment_method: str = Field(min_length=1, max_length=30)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class SaleCreate(BaseModel):
    items: list[SaleItemCreate] = Field(min_length=1)
    customers: list[SaleCustomerCreate] = Field(default_factory=list)
    payments: list[SalePaymentCreate] = Field(min_length=1)
    discount_percentage: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        le=100,
        max_digits=7,
        decimal_places=4,
    )


class SaleItemRead(BaseModel):
    id: UUID
    product_id: int
    product_code: str
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal

    model_config = {"from_attributes": True}


class SaleCustomerRead(BaseModel):
    id: UUID
    client_id: UUID | None
    customer_name: str
    allocation_percentage: Decimal
    allocation_amount: Decimal
    is_generic: bool

    model_config = {"from_attributes": True}


class SalePaymentRead(BaseModel):
    id: UUID
    payment_method: str
    amount: Decimal

    model_config = {"from_attributes": True}


class SaleRead(BaseModel):
    id: UUID
    tenant_id: int
    sale_number: str
    status: str
    subtotal: Decimal
    discount_percentage: Decimal
    discount_amount: Decimal
    total: Decimal
    items: list[SaleItemRead]
    customers: list[SaleCustomerRead]
    payments: list[SalePaymentRead]

    model_config = {"from_attributes": True}
