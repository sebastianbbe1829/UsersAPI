from fastapi import Depends
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import GlobalUserDB, UserTenantDB
from ..schemas import LoginRequest, SuperLoginRequest
from ..settings import settings

from ..services.auth_context_service import get_current_user_from_token
from ..services.auth_audit_service import (
    close_login_session,
    create_login_session,
    refresh_login_session,
)
from ..services.auth_service import (
    create_access_token as create_access_token_service,
    login_user as login_user_service,
    oauth2_scheme,
    verify_password as verify_password_service,
)
from ..services.global_auth_service import (
    get_current_super_user,
    login_super_user as login_super_user_service,
)
from ..services.token_validation_service import validate_token as validate_token_service


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return verify_password_service(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta=None) -> str:
    return create_access_token_service(data, expires_delta)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserTenantDB | GlobalUserDB:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"verify_exp": False},
        )
    except JWTError:
        return get_current_user_from_token(token, db)

    if payload.get("user_type") == "SUPER":
        return get_current_super_user(token, db)

    return get_current_user_from_token(token, db)


def _audit_login(
    result,
    db: Session,
    client_ip: str | None,
    user_agent: str | None,
):
    token = (
        result.access_token
        if hasattr(result, "access_token")
        else result["access_token"]
    )
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
        options={"verify_exp": False},
    )
    create_login_session(
        db,
        token,
        payload,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    return result


def login_user(
    datos: LoginRequest,
    db: Session,
    client_ip: str | None = None,
    user_agent: str | None = None,
):
    if datos.super_mode:
        super_datos = SuperLoginRequest(
            email=datos.username,
            password=datos.password,
            otp=datos.otp,
            tenant=datos.tenant,
        )
        result = login_super_user_service(
            super_datos,
            db,
            client_ip=client_ip,
        )
    else:
        result = login_user_service(
            datos,
            db,
            client_ip=client_ip,
            user_agent=user_agent,
        )

    return _audit_login(result, db, client_ip, user_agent)


def login_super_user(
    datos: SuperLoginRequest,
    db: Session,
    client_ip: str | None = None,
    user_agent: str | None = None,
):
    result = login_super_user_service(
        datos,
        db,
        client_ip=client_ip,
    )
    return _audit_login(result, db, client_ip, user_agent)


def logout_user(
    token: str,
    db: Session,
    client_ip: str | None = None,
    user_agent: str | None = None,
):
    close_login_session(
        db,
        token,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    return {"message": "Sesión cerrada correctamente"}


def refresh_user_session(
    token: str,
    db: Session,
    client_ip: str | None = None,
    user_agent: str | None = None,
):
    return refresh_login_session(
        db,
        token,
        client_ip=client_ip,
        user_agent=user_agent,
    )


def validate_token(token: str, db: Session):
    return validate_token_service(token, db)
