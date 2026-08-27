from pydantic import BaseModel, EmailStr, Field


class SuperBootstrapRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)


class SuperBootstrapResponse(BaseModel):
    id: int
    email: EmailStr
    mfa_enabled: bool
    provisioning_uri: str


class SuperBootstrapMfaVerifyRequest(BaseModel):
    user_id: int
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class SuperBootstrapMfaVerifyResponse(BaseModel):
    id: int
    email: EmailStr
    mfa_enabled: bool
    mfa_verified: bool


class SuperLoginRequest(BaseModel):
    email: EmailStr
    password: str
    otp: str | None = Field(default=None, min_length=6, max_length=6)
    tenant: str = Field(min_length=1, max_length=100)


class SuperLoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_type: str
    session_id: str
    tenant_id: int
    tenant_slug: str
