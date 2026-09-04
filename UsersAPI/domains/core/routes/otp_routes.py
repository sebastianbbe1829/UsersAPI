from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from ..controllers.otp_controller import (
    create_otp,
    validate_otp_api_key,
    verify_otp,
)
from ..database import get_db
from ..schemas.otp import (
    OTPGenerateRequest,
    OTPGenerateResponse,
    OTPValidateRequest,
    OTPValidateResponse,
)
from ..security.rate_limiter import (
    OTP_GENERATE_LIMIT,
    OTP_GENERATE_WINDOW,
    OTP_VALIDATE_LIMIT,
    OTP_VALIDATE_WINDOW,
    rate_limiter,
)


otp_routes = APIRouter(
    prefix="/otp",
    tags=["OTP"],
)


@otp_routes.post(
    "/generate",
    response_model=OTPGenerateResponse,
    summary="Generar OTP temporal",
)
def create_otp_route(
    datos: OTPGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
    x_otp_api_key: str = Header(..., alias="X-OTP-API-Key"),
):
    validate_otp_api_key(x_otp_api_key)
    client_ip = rate_limiter.client_ip(request)
    destination = rate_limiter.normalize(datos.destination)
    purpose = rate_limiter.normalize(datos.purpose)

    rate_limiter.check(
        f"otp:generate:ip:{client_ip}",
        OTP_GENERATE_LIMIT,
        OTP_GENERATE_WINDOW,
    )
    rate_limiter.check(
        f"otp:generate:destination:{purpose}:{destination}",
        OTP_GENERATE_LIMIT,
        OTP_GENERATE_WINDOW,
    )

    return create_otp(datos, db)


@otp_routes.post(
    "/validate",
    response_model=OTPValidateResponse,
    summary="Validar OTP temporal",
)
def verify_otp_route(
    datos: OTPValidateRequest,
    request: Request,
    db: Session = Depends(get_db),
    x_otp_api_key: str = Header(..., alias="X-OTP-API-Key"),
):
    validate_otp_api_key(x_otp_api_key)
    client_ip = rate_limiter.client_ip(request)
    destination = rate_limiter.normalize(datos.destination)
    purpose = rate_limiter.normalize(datos.purpose)

    rate_limiter.check(
        f"otp:validate:ip:{client_ip}",
        OTP_VALIDATE_LIMIT,
        OTP_VALIDATE_WINDOW,
    )
    rate_limiter.check(
        f"otp:validate:destination:{purpose}:{destination}",
        OTP_VALIDATE_LIMIT,
        OTP_VALIDATE_WINDOW,
    )

    return verify_otp(datos, db)
