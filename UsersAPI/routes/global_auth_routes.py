from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from ..controllers import global_auth_controller
from ..database import get_db
from ..schemas import (
    SuperBootstrapRequest,
    SuperBootstrapResponse,
    SuperLoginRequest,
    SuperLoginResponse,
)


global_auth_routes = APIRouter(
    prefix="/auth/super",
    tags=["Auth SUPER"],
)


@global_auth_routes.post(
    "/bootstrap",
    response_model=SuperBootstrapResponse,
    summary="Crear el primer usuario SUPER",
)
def bootstrap_super_user(
    datos: SuperBootstrapRequest,
    x_super_bootstrap_secret: str = Header(...),
    db: Session = Depends(get_db),
):
    return global_auth_controller.bootstrap_super_user(
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
    return global_auth_controller.login_super_user(
        datos,
        request,
        db,
    )
