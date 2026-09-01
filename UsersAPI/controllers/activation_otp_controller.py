from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..schemas.activation_otp import (
    ActivationOTPGenerateResponse,
    ActivationOTPValidateRequest,
    ActivationOTPValidateResponse,
)
from ..services.activation_otp_service import (
    generate_activation_otp,
    validate_activation_otp,
)


def request_activation_otp(
    dni: str,
    token: str,
    db: Session,
) -> ActivationOTPGenerateResponse:
    try:
        expires_at = generate_activation_otp(
            dni=dni,
            token=token,
            db=db,
        )
        return ActivationOTPGenerateResponse(
            message="Código de verificación enviado correctamente.",
            expires_at=expires_at,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No fue posible generar o enviar el código de activación.",
        ) from exc


def verify_activation_otp(
    dni: str,
    token: str,
    datos: ActivationOTPValidateRequest,
    db: Session,
) -> ActivationOTPValidateResponse:
    valid = validate_activation_otp(
        dni=dni,
        token=token,
        code=datos.code,
        db=db,
    )

    return ActivationOTPValidateResponse(
        valid=valid,
        message=(
            "Cuenta activada correctamente."
            if valid
            else "Código OTP inválido, expirado, consumido o bloqueado."
        ),
    )
