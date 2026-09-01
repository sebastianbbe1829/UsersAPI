import secrets

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..schemas.otp import (
    OTPGenerateRequest,
    OTPGenerateResponse,
    OTPValidateRequest,
    OTPValidateResponse,
)
from ..services.otp_service import generate_otp, validate_otp
from ..settings import settings


def validate_otp_api_key(x_otp_api_key: str) -> None:
    if not settings.otp_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OTP_API_KEY no está configurada.",
        )

    if not secrets.compare_digest(x_otp_api_key, settings.otp_api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clave de OTP inválida.",
        )


def create_otp(
    datos: OTPGenerateRequest,
    db: Session,
) -> OTPGenerateResponse:
    try:
        expires_at = generate_otp(
            db,
            destination=datos.destination,
            purpose=datos.purpose,
        )
        return OTPGenerateResponse(
            message="Código OTP enviado correctamente.",
            expires_at=expires_at,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No fue posible generar o enviar el código OTP.",
        ) from exc


def verify_otp(
    datos: OTPValidateRequest,
    db: Session,
) -> OTPValidateResponse:
    valid = validate_otp(
        db,
        destination=datos.destination,
        purpose=datos.purpose,
        code=datos.code,
    )

    return OTPValidateResponse(
        valid=valid,
        message=(
            "Código OTP válido."
            if valid
            else "Código OTP inválido, expirado, consumido o bloqueado."
        ),
    )
