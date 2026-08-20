from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoleCreate(BaseModel):

    code: str
    name: str
    description: str | None = None


class RoleUpdate(BaseModel):

    code: str | None = None
    name: str | None = None
    description: str | None = None


class RoleRead(BaseModel):

    id: int
    tenant_id: int | None
    code: str
    name: str
    description: str | None
    status: int
    created_at: datetime
    created_by: str

    model_config = ConfigDict(
        from_attributes=True
    )


class RoleDeleteResponse(BaseModel):

    id: int
    tenant_id: int | None
    code: str
    name: str
    status: int
    message: str