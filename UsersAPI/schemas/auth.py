from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str
    tenant: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    tenant_id: int
    tenant_slug: str
    user_tenant_id: int