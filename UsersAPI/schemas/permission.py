from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PermissionCreate(BaseModel):

    code: str
    name: str
    description: str | None = None


class PermissionUpdate(BaseModel):

    code: str | None = None
    name: str | None = None
    description: str | None = None
    status: int | None = None


class PermissionRead(BaseModel):

    id: int
    code: str
    name: str
    description: str | None
    status: int
    created_at: datetime
    created_by: str

    model_config = ConfigDict(
        from_attributes=True
    )


class PermissionResponse(BaseModel):

    id: int
    code: str
    name: str
    status: int