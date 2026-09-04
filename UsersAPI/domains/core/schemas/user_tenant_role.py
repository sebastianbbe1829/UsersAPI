from pydantic import BaseModel, ConfigDict


class UserTenantRoleCreate(BaseModel):
    user_tenant_id: int
    role_id: int


class UserTenantRoleRead(BaseModel):
    id: int
    user_tenant_id: int
    role_id: int

    model_config = ConfigDict(from_attributes=True)


class UserTenantRoleDeleteResponse(BaseModel):
    id: int
    user_tenant_id: int
    role_id: int
    message: str