from pydantic import BaseModel, EmailStr, Field


class SuperBootstrapRequest(BaseModel):
    bootstrap_secret: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=12)


class SuperBootstrapResponse(BaseModel):
    id: int
    email: EmailStr
    mfa_enabled: bool
    mfa_secret: str
    provisioning_uri: str


class SuperLoginRequest(BaseModel):
    email: EmailStr
    password: str
    otp: str | None = Field(default=None, min_length=6, max_length=6)


class SuperLoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_type: str
    session_id: str
