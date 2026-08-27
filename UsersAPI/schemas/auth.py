from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str
    tenant: str
    super_mode: bool = False


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_type: str = "TENANT"
    tenant_id: int | None = None
    tenant_slug: str | None = None


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