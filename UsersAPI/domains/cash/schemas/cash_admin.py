from datetime import datetime

from pydantic import BaseModel, Field


class BranchCreate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=2, max_length=150)
    address: str | None = Field(default=None, max_length=250)
    phone: str | None = Field(default=None, max_length=30)


class BranchUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=2, max_length=150)
    address: str | None = Field(default=None, max_length=250)
    phone: str | None = Field(default=None, max_length=30)
    status: int | None = Field(default=None, ge=0, le=1)


class BranchRead(BaseModel):
    id: int
    tenant_id: int
    code: str
    name: str
    address: str | None
    phone: str | None
    status: int
    created_at: datetime
    created_by: str
    updated_at: datetime | None
    updated_by: str | None
    cash_boxes_count: int = 0


class CashBoxCreate(BaseModel):
    branch_id: int = Field(gt=0)
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=2, max_length=100)


class CashBoxUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=2, max_length=100)
    status: int | None = Field(default=None, ge=0, le=1)


class CashBoxRead(BaseModel):
    id: int
    tenant_id: int
    branch_id: int
    branch_name: str
    code: str
    name: str
    status: int
    created_at: datetime
    created_by: str
    updated_at: datetime | None
    updated_by: str | None


class CashAssignmentCreate(BaseModel):
    user_tenant_id: int = Field(gt=0)
    branch_id: int = Field(gt=0)
    cash_box_id: int = Field(gt=0)


class CashAssignmentRead(BaseModel):
    id: int
    tenant_id: int
    user_tenant_id: int
    user_name: str
    user_dni: str
    user_email: str
    branch_id: int
    branch_name: str
    cash_box_id: int
    cash_box_name: str
    cash_box_code: str
    status: int
    assigned_at: datetime
    assigned_by: str
    unassigned_at: datetime | None
    unassigned_by: str | None
