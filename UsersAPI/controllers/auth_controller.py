from fastapi import Depends
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import GlobalUserDB, UserTenantDB
from ..schemas import LoginRequest
from ..settings import settings

from ..services.auth_service import (
    create_access_token as create_access_token_service,
    get_current_user as get_current_user_service,
    get_password_hash as get_password_hash_service,
    login_user as login_user_service,
    oauth2_scheme,
    validate_token as validate_token_service,
    verify_password as verify_password_service,
)
from ..services.auth_service import pwd_context
from ..services.global_auth_service import get_current_super_user


# ============================================================
# PASSWORD
# ============================================================


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return verify_password_service(
        plain_password,
        hashed_password,
    )


def get_password_hash(
    password: str,
) -> str:
    return get_password_hash_service(password)


# ============================================================
# JWT
# ============================================================


def create_access_token(
    data: dict,
    expires_delta=None,
) -> str:
    return create_access_token_service(
        data,
        expires_delta,
    )


# ============================================================
# CURRENT USER
#
# Distingue identidad tenant de identidad SUPER.
#
# El SUPER todavía NO obtiene contexto RLS aquí.
# Eso ocurrirá en la fase de selección de tenant.
# ============================================================


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
        return get_current_user_service(
            token,
            db,
        )

    if payload.get("user_type") == "SUPER":
        return get_current_super_user(
            token,
            db,
        )

    return get_current_user_service(
        token,
        db,
    )


# ============================================================
# LOGIN
# ============================================================


def login_user(
    datos: LoginRequest,
    db: Session,
):
    return login_user_service(
        datos,
        db,
    )


# ============================================================
# VALIDATE TOKEN
# ============================================================


def validate_token(
    token: str,
    db: Session,
):
    return validate_token_service(
        token,
        db,
    )
