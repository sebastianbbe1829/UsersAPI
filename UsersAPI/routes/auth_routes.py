from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..controllers import auth_controller
from ..database import get_db
from ..models import GlobalUserDB, UserTenantDB
from ..schemas import (
    LoginRequest,
    LoginResponse,
    TokenValidationResponse,
)
from ..security.rate_limiter import (
    LOGIN_ACCOUNT_LIMIT,
    LOGIN_ACCOUNT_WINDOW,
    LOGIN_IP_LIMIT,
    LOGIN_IP_WINDOW,
    SUPER_LOGIN_LIMIT,
    SUPER_LOGIN_WINDOW,
    SUPER_MFA_LIMIT,
    SUPER_MFA_WINDOW,
    rate_limiter,
)


auth_routers = APIRouter(
    prefix="/auth",
    tags=["Autenticación"],
)


@auth_routers.post(
    "/login",
    response_model=LoginResponse,
    summary="Autenticar usuario en un tenant o como SUPER",
)
def login(
    datos: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = rate_limiter.client_ip(request)
    username = rate_limiter.normalize(datos.username)

    if datos.super_mode:
        rate_limiter.check(
            f"login:super:ip:{client_ip}",
            SUPER_LOGIN_LIMIT,
            SUPER_LOGIN_WINDOW,
        )
        rate_limiter.check(
            f"login:super:account:{username}",
            SUPER_LOGIN_LIMIT,
            SUPER_LOGIN_WINDOW,
        )
        if datos.otp:
            rate_limiter.check(
                f"login:super:mfa:{username}",
                SUPER_MFA_LIMIT,
                SUPER_MFA_WINDOW,
            )
    else:
        rate_limiter.check(
            f"login:ip:{client_ip}",
            LOGIN_IP_LIMIT,
            LOGIN_IP_WINDOW,
        )
        tenant = rate_limiter.normalize(datos.tenant)
        rate_limiter.check(
            f"login:account:{tenant}:{username}",
            LOGIN_ACCOUNT_LIMIT,
            LOGIN_ACCOUNT_WINDOW,
        )

    return auth_controller.login_user(
        datos,
        db,
        client_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
    )


@auth_routers.post(
    "/logout",
    summary="Cerrar la sesión autenticada y registrar su duración",
)
def logout(
    request: Request,
    token: str = Depends(auth_controller.oauth2_scheme),
    db: Session = Depends(get_db),
):
    client_ip = rate_limiter.client_ip(request)
    return auth_controller.logout_user(
        token,
        db,
        client_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
    )


@auth_routers.get(
    "/validate",
    response_model=TokenValidationResponse,
    summary="Validar token JWT",
)
def validate(
    token: str = Depends(auth_controller.oauth2_scheme),
    _current_user: UserTenantDB | GlobalUserDB = Depends(auth_controller.get_current_user),
    db: Session = Depends(get_db),
):
    return auth_controller.validate_token(
        token,
        db,
    )
