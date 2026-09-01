from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import (
    OTPGenerateRequest,
    OTPGenerateResponse,
    OTPValidateRequest,
    OTPValidateResponse,
)
from ..services.otp_service import generate_otp, validate_otp
from ..settings import settings
from ..util.email_utils import send_email


otp_routes = APIRouter(
    prefix="/otp",
    tags=["OTP"],
)


def _validate_otp_api_key(x_otp_api_key: str) -> None:
    if not settings.otp_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OTP_API_KEY no está configurada.",
        )

    import secrets

    if not secrets.compare_digest(x_otp_api_key, settings.otp_api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clave de OTP inválida.",
        )


@otp_routes.post(
    "/generate",
    response_model=OTPGenerateResponse,
    summary="Generar OTP temporal",
)
def create_otp(
    datos: OTPGenerateRequest,
    db: Session = Depends(get_db),
    x_otp_api_key: str = Header(..., alias="X-OTP-API-Key"),
):
    """Genera un OTP para pruebas y futuros flujos transaccionales.

    El código nunca se devuelve en la respuesta HTTP; se envía al destino
    indicado por correo. El endpoint está protegido por una clave propia
    de OTP, independiente de la autenticación del servicio de email.
    """
    _validate_otp_api_key(x_otp_api_key)

    try:
        otp, code = generate_otp(
            db,
            destination=datos.destination,
            purpose=datos.purpose,
        )

        send_email(
            recipient=datos.destination,
            subject="Código de verificación OTP",
            message=(
                "Tu código de verificación es:\n\n"
                f"{code}\n\n"
                f"Este código vence en {settings.otp_expire_minutes} minutos.\n"
                "Si no solicitaste este código, puedes ignorar este correo."
            ),
            template="otp",
        )

        db.commit()

        return OTPGenerateResponse(
            message="Código OTP enviado correctamente.",
            expires_at=otp.expires_at,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No fue posible generar o enviar el código OTP.",
        )


@otp_routes.post(
    "/validate",
    response_model=OTPValidateResponse,
    summary="Validar OTP temporal",
)
def verify_otp(
    datos: OTPValidateRequest,
    db: Session = Depends(get_db),
    x_otp_api_key: str = Header(..., alias="X-OTP-API-Key"),
):
    _validate_otp_api_key(x_otp_api_key)

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
