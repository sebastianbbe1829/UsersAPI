from datetime import datetime

from pydantic import BaseModel, Field


class ActivationOTPGenerateResponse(BaseModel):
    message: str
    expires_at: datetime


class ActivationOTPValidateRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=12)


class ActivationOTPValidateResponse(BaseModel):
    valid: bool
    message: str
