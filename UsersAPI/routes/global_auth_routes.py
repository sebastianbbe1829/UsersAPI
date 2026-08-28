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


global_auth_routes = APIRouter(
    prefix="/auth/super",
    tags=["Autenticación SUPER"],
)


# ============================================================
# BOOTSTRAP DEL PRIMER USUARIO SUPER
#
# Utiliza exclusivamente la conexión de bootstrap.
#
# Este endpoint NO utiliza la conexión normal porque:
# - todavía no existe un usuario SUPER
# - todavía no existe una sesión SUPER
# - el acceso se controla mediante X-Super-Bootstrap-Secret
# ============================================================

@global_auth_routes.post(
    "/bootstrap",
    response_model=SuperBootstrapResponse,
    summary="Crear el primer usuario SUPER",
)
def bootstrap_super_user(
    datos: SuperBootstrapRequest,
    x_super_bootstrap_secret: str = Header(...),
    db: Session = Depends(get_bootstrap_db),
):
    return global_auth_controller.bootstrap_super_user(
        datos,
        x_super_bootstrap_secret,
        db,
    )


# ============================================================
# VERIFICAR MFA INICIAL DEL USUARIO SUPER
#
# Todavía forma parte del proceso de bootstrap, por lo tanto
# también utiliza exclusivamente la conexión de bootstrap.
# ============================================================

@global_auth_routes.post(
    "/bootstrap/verify-mfa",
    response_model=SuperBootstrapMfaVerifyResponse,
    summary="Verificar el MFA inicial del usuario SUPER",
)
def verify_bootstrap_mfa(
    datos: SuperBootstrapMfaVerifyRequest,
    x_super_bootstrap_secret: str = Header(...),
    db: Session = Depends(get_bootstrap_db),
):
    return global_auth_bootstrap_controller.verify_bootstrap_mfa(
        datos,
        x_super_bootstrap_secret,
        db,
    )


# ============================================================
# LOGIN SUPER
#
# A partir de aquí ya NO estamos en bootstrap.
# El login utiliza la conexión normal de la aplicación.
# ============================================================

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
    return global_auth_controller.login_super_user(
        datos,
        request,
        db,
    )