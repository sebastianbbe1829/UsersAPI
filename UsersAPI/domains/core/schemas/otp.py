from datetime import datetime

from pydantic import BaseModel, Field


class OTPGenerateRequest(BaseModel):
    destination: str = Field(..., min_length=3, max_length=320)
    purpose: str = Field(..., min_length=1, max_length=50)


class OTPGenerateResponse(BaseModel):
    message: str
    expires_at: datetime


class OTPValidateRequest(BaseModel):
    destination: str = Field(..., min_length=3, max_length=320)
    purpose: str = Field(..., min_length=1, max_length=50)
    code: str = Field(..., min_length=4, max_length=12)


class OTPValidateResponse(BaseModel):
    valid: bool
    message: str
