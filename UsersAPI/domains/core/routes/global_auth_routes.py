from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from ..controllers import global_auth_bootstrap_controller, global_auth_controller
from ..database import get_bootstrap_db, get_db
from ..schemas import (
    SuperBootstrapMfaVerifyRequest,
    SuperBootstrapMfaVerifyResponse,
    SuperBootstrapRequest,
    SuperBootstrapResponse,
    SuperLoginRequest,
    SuperLoginResponse,
)
from ..security.rate_limiter import (
    SUPER_BOOTSTRAP_LIMIT,
    SUPER_BOOTSTRAP_WINDOW,
    SUPER_LOGIN_LIMIT,
    SUPER_LOGIN_WINDOW,
    SUPER_MFA_LIMIT,
    SUPER_MFA_WINDOW,
    rate_limiter,
)


global_auth_routes = APIRouter(
    prefix="/auth/super",
    tags=["Autenticación SUPER"],
)


@global_auth_routes.post(
    "/bootstrap",
    response_model=SuperBootstrapResponse,
    summary="Crear el primer usuario SUPER",
)
def bootstrap_super_user(
    datos: SuperBootstrapRequest,
    request: Request,
    x_super_bootstrap_secret: str = Header(...),
    db: Session = Depends(get_bootstrap_db),
):
    client_ip = rate_limiter.client_ip(request)
    rate_limiter.check(
        f"super:bootstrap:ip:{client_ip}",
        SUPER_BOOTSTRAP_LIMIT,
        SUPER_BOOTSTRAP_WINDOW,
    )
    return global_auth_controller.bootstrap_super_user(
        datos,
        x_super_bootstrap_secret,
        db,
    )


@global_auth_routes.post(
    "/bootstrap/verify-mfa",
    response_model=SuperBootstrapMfaVerifyResponse,
    summary="Verificar el MFA inicial del usuario SUPER",
)
def verify_bootstrap_mfa(
    datos: SuperBootstrapMfaVerifyRequest,
    request: Request,
    x_super_bootstrap_secret: str = Header(...),
    db: Session = Depends(get_bootstrap_db),
):
    client_ip = rate_limiter.client_ip(request)
    rate_limiter.check(
        f"super:bootstrap:mfa:ip:{client_ip}",
        SUPER_MFA_LIMIT,
        SUPER_MFA_WINDOW,
    )
    return global_auth_bootstrap_controller.verify_bootstrap_mfa(
        datos,
        x_super_bootstrap_secret,
        db,
    )


@global_auth_routes.post(
    "/login",
    response_model=SuperLoginResponse,
    summary="Autenticar usuario SUPER con MFA",
)
def login_super_user(
    datos: SuperLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = rate_limiter.client_ip(request)
    email = rate_limiter.normalize(datos.email)

    rate_limiter.check(
        f"super:login:ip:{client_ip}",
        SUPER_LOGIN_LIMIT,
        SUPER_LOGIN_WINDOW,
    )
    rate_limiter.check(
        f"super:login:account:{email}",
        SUPER_LOGIN_LIMIT,
        SUPER_LOGIN_WINDOW,
    )
    if datos.otp:
        rate_limiter.check(
            f"super:mfa:{email}",
            SUPER_MFA_LIMIT,
            SUPER_MFA_WINDOW,
        )

    return global_auth_controller.login_super_user(
        datos,
        request,
        db,
    )
