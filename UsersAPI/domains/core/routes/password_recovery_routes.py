from fastapi import APIRouter, Depends, Path, Request
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
from UsersAPI.security.rate_limiter import (
    PASSWORD_RECOVERY_REQUEST_LIMIT,
    PASSWORD_RECOVERY_REQUEST_WINDOW,
    PASSWORD_RECOVERY_RESET_LIMIT,
    PASSWORD_RECOVERY_RESET_WINDOW,
    rate_limiter,
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
    request: Request,
    tenant_slug: str = Path(..., min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    client_ip = rate_limiter.client_ip(request)
    email = rate_limiter.normalize(str(datos.email))
    tenant = rate_limiter.normalize(tenant_slug)

    rate_limiter.check(
        f"password-recovery:request:ip:{client_ip}",
        PASSWORD_RECOVERY_REQUEST_LIMIT,
        PASSWORD_RECOVERY_REQUEST_WINDOW,
    )
    rate_limiter.check(
        f"password-recovery:request:account:{tenant}:{email}",
        PASSWORD_RECOVERY_REQUEST_LIMIT,
        PASSWORD_RECOVERY_REQUEST_WINDOW,
    )

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
    request: Request,
    tenant_slug: str = Path(..., min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    client_ip = rate_limiter.client_ip(request)
    email = rate_limiter.normalize(str(datos.email))
    tenant = rate_limiter.normalize(tenant_slug)

    rate_limiter.check(
        f"password-recovery:reset:ip:{client_ip}",
        PASSWORD_RECOVERY_RESET_LIMIT,
        PASSWORD_RECOVERY_RESET_WINDOW,
    )
    rate_limiter.check(
        f"password-recovery:reset:account:{tenant}:{email}",
        PASSWORD_RECOVERY_RESET_LIMIT,
        PASSWORD_RECOVERY_RESET_WINDOW,
    )

    return reset_recovered_password(
        tenant_slug=tenant_slug,
        datos=datos,
        db=db,
    )
