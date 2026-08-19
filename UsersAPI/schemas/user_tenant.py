from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserTenantCreate(BaseModel):
    user_id: int
    tenant_id: int


class UserTenantRead(BaseModel):
    id: int
    user_id: int
    tenant_id: int
    status: int
    created_at: datetime
    created_by: str

    model_config = ConfigDict(from_attributes=True)


class UserTenantDeleteResponse(BaseModel):
    id: int
    user_id: int
    tenant_id: int
    status: int
    message: str