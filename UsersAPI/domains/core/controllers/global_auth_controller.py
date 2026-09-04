from fastapi import Request
from jose import jwt
from sqlalchemy.orm import Session

from ..schemas import SuperBootstrapRequest, SuperLoginRequest
from ..services.auth_audit_service import create_login_session
from ..services.global_auth_service import (
    bootstrap_super_user as bootstrap_super_user_service,
    login_super_user as login_super_user_service,
)
from ..settings import settings


def bootstrap_super_user(
    datos: SuperBootstrapRequest,
    bootstrap_secret: str,
    db: Session,
):
    return bootstrap_super_user_service(
        datos,
        bootstrap_secret,
        db,
    )


def login_super_user(
    datos: SuperLoginRequest,
    request: Request,
    db: Session,
):
    client_ip = request.client.host if request.client else None

    result = login_super_user_service(
        datos,
        db,
        client_ip=client_ip,
    )
    payload = jwt.decode(
        result.access_token,
        settings.secret_key,
        algorithms=[settings.algorithm],
        options={"verify_exp": False},
    )
    create_login_session(
        db,
        result.access_token,
        payload,
        client_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
    )
    return result
