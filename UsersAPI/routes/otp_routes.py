from fastapi import APIRouter, Depends, Header
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
    db: Session = Depends(get_db),
    x_otp_api_key: str = Header(..., alias="X-OTP-API-Key"),
):
    """Genera un OTP para pruebas y futuros flujos transaccionales."""
    validate_otp_api_key(x_otp_api_key)
    return create_otp(datos, db)


@otp_routes.post(
    "/validate",
    response_model=OTPValidateResponse,
    summary="Validar OTP temporal",
)
def verify_otp_route(
    datos: OTPValidateRequest,
    db: Session = Depends(get_db),
    x_otp_api_key: str = Header(..., alias="X-OTP-API-Key"),
):
    validate_otp_api_key(x_otp_api_key)
    return verify_otp(datos, db)
