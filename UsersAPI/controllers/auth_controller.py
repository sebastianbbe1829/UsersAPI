from fastapi import Depends
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import GlobalUserDB, UserTenantDB
from ..schemas import LoginRequest, SuperLoginRequest
from ..settings import settings

from ..services.auth_context_service import get_current_user_from_token
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
from ..services.password_service import get_password_hash
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


def login_user(
    datos: LoginRequest,
    db: Session,
    client_ip: str | None = None,
):
    if datos.super_mode:
        super_datos = SuperLoginRequest(
            email=datos.username,
            password=datos.password,
            otp=datos.otp,
            tenant=datos.tenant,
        )
        return login_super_user_service(super_datos, db, client_ip=client_ip)

    return login_user_service(datos, db)


def login_super_user(
    datos: SuperLoginRequest,
    db: Session,
    client_ip: str | None = None,
):
    return login_super_user_service(datos, db, client_ip=client_ip)


def validate_token(token: str, db: Session):
    return validate_token_service(token, db)
