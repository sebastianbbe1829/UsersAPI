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


class TokenUserResponse(BaseModel):
    dni: str
    email: str


class TokenTenantResponse(BaseModel):
    id: int
    slug: str


class TokenValidationResponse(BaseModel):
    valid: bool
    expiration: int
    now: int
    remaining_seconds: int | None
    remaining_minutes_rounded: int | None
    user: TokenUserResponse
    tenant: TokenTenantResponse
    user_tenant_id: int