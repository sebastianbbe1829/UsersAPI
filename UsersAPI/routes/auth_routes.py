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


auth_routers = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


# ============================================================
# LOGIN
# POST /auth/login
#
# Endpoint público.
#
# super_mode=False:
#     Login normal del tenant.
#
# super_mode=True:
#     Login SUPER + MFA.
# ============================================================

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

    client_ip = request.client.host if request.client else None

    return auth_controller.login_user(
        datos,
        db,
        client_ip=client_ip,
    )


# ============================================================
# VALIDAR TOKEN
# GET /auth/validate
#
# Requiere un JWT válido y no expirado.
#
# get_current_user realiza la validación criptográfica completa
# del JWT, incluyendo la expiración. Después se ejecuta la
# consulta de validación para devolver la información del token.
# ============================================================

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
