from sqlalchemy.orm import Session

from ..schemas.password_recovery import (
    PasswordRecoveryRequest,
    PasswordRecoveryResponse,
    PasswordResetRequest,
    PasswordResetResponse,
)
from ..services.password_recovery_service import (
    request_password_recovery,
    reset_password,
)


def request_recovery(
    tenant_slug: str,
    datos: PasswordRecoveryRequest,
    db: Session,
) -> PasswordRecoveryResponse:
    expires_at = request_password_recovery(
        tenant_slug=tenant_slug,
        email=str(datos.email),
        db=db,
    )

    return PasswordRecoveryResponse(
        message=(
            "Si el correo pertenece a un usuario activo, "
            "recibirás un código para recuperar tu contraseña."
        ),
        expires_at=expires_at,
    )


def reset_recovered_password(
    tenant_slug: str,
    datos: PasswordResetRequest,
    db: Session,
) -> PasswordResetResponse:
    resultado = reset_password(
        tenant_slug=tenant_slug,
        email=str(datos.email),
        code=datos.code,
        new_password=datos.new_password,
        db=db,
    )

    return PasswordResetResponse(**resultado)
