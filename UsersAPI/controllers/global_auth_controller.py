from fastapi import Request
from sqlalchemy.orm import Session

from ..schemas import SuperBootstrapRequest, SuperLoginRequest
from ..services.global_auth_service import (
    bootstrap_super_user as bootstrap_super_user_service,
    login_super_user as login_super_user_service,
)


def bootstrap_super_user(
    datos: SuperBootstrapRequest,
    db: Session,
):
    return bootstrap_super_user_service(
        datos,
        db,
    )


def login_super_user(
    datos: SuperLoginRequest,
    request: Request,
    db: Session,
):
    response = login_super_user_service(
        datos,
        db,
    )

    return response
