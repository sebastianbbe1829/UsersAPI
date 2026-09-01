from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from ..controllers.password_recovery_controller import (
    request_recovery,
    reset_recovered_password,
)
from ..database import get_db
from ..schemas.password_recovery import (
    PasswordRecoveryRequest,
    PasswordRecoveryResponse,
    PasswordResetRequest,
    PasswordResetResponse,
)

password_recovery_routes = APIRouter(
    prefix="/auth/password-recovery",
    tags=["Recuperación de contraseña"],
)


@password_recovery_routes.post(
    "/{tenant_slug}/request",
    response_model=PasswordRecoveryResponse,
    summary="Solicitar código OTP para recuperar contraseña",
)
def request_password_recovery(
    datos: PasswordRecoveryRequest,
    tenant_slug: str = Path(..., min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    return request_recovery(
        tenant_slug=tenant_slug,
        datos=datos,
        db=db,
    )


@password_recovery_routes.post(
    "/{tenant_slug}/reset",
    response_model=PasswordResetResponse,
    summary="Validar OTP y establecer nueva contraseña",
)
def reset_password(
    datos: PasswordResetRequest,
    tenant_slug: str = Path(..., min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    return reset_recovered_password(
        tenant_slug=tenant_slug,
        datos=datos,
        db=db,
    )
