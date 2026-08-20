import math

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import UserTenantDB, TenantDB
from ..schemas import LoginRequest
from ..settings import settings


# ============================================================
# CONFIGURACIÓN
# ============================================================

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/login",
)


# ============================================================
# PASSWORD
# ============================================================


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:

    try:
        return pwd_context.verify(
            plain_password,
            hashed_password,
        )

    except Exception as exc:
        logger.error(
            "Error validando password: %s",
            exc,
        )

        return False


def get_password_hash(
    password: str,
) -> str:

    return pwd_context.hash(password)


# ============================================================
# JWT
# ============================================================


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update(
        {
            "exp": expire,
        }
    )

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


# ============================================================
# LOGIN MULTI-TENANT
# ============================================================


def login_user(
    datos: LoginRequest,
    db: Session,
):

    logger.info(
        "Intento login usuario=%s tenant=%s",
        datos.username,
        datos.tenant,
    )

    user_tenant = (
        db.query(UserTenantDB)
        .join(
            TenantDB,
            UserTenantDB.tenant_id == TenantDB.id,
        )
        .filter(
            UserTenantDB.email == datos.username,
            TenantDB.slug == datos.tenant,
            UserTenantDB.status == 1,
            TenantDB.status == 1,
        )
        .first()
    )

    if user_tenant is None:

        logger.warning(
            "Usuario no encontrado en tenant",
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credenciales inválidas o usuario inactivo",
        )

    if not verify_password(
        datos.password,
        user_tenant.password,
    ):

        logger.warning(
            "Password inválido usuario=%s",
            datos.username,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credenciales inválidas",
        )

    tenant = user_tenant.tenant
    usuario = user_tenant.user

    access_token = create_access_token(
        {
            "sub": usuario.dni,
            "tenant_id": tenant.id,
            "tenant_slug": tenant.slug,
            "user_tenant_id": user_tenant.id,
        }
    )

    logger.info(
        "Login exitoso usuario=%s tenant=%s",
        datos.username,
        tenant.slug,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "tenant_id": tenant.id,
        "tenant_slug": tenant.slug,
        "user_tenant_id": user_tenant.id,
    }


# ============================================================
# CURRENT USER
# ============================================================


def get_current_user(
    token: str,
    db: Session,
) -> UserTenantDB:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_tenant_id = payload.get(
            "user_tenant_id"
        )

        if user_tenant_id is None:
            raise credentials_exception

    except ExpiredSignatureError as exc:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        ) from exc

    except JWTError as exc:

        raise credentials_exception from exc

    user_tenant = (
        db.query(UserTenantDB)
        .join(
            TenantDB,
            UserTenantDB.tenant_id == TenantDB.id,
        )
        .filter(
            UserTenantDB.id == user_tenant_id,
            UserTenantDB.status == 1,
            TenantDB.status == 1,
        )
        .first()
    )

    if user_tenant is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no pertenece al tenant",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    return user_tenant


# ============================================================
# CURRENT USER TENANT
# ============================================================


def get_current_user_tenant(
    token: str,
    db: Session,
) -> UserTenantDB:

    return get_current_user(
        token,
        db,
    )


# ============================================================
# VALIDATE TOKEN
# ============================================================


def validate_token(
    token: str,
    db: Session,
):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={
                "verify_exp": False,
            },
        )

        exp = payload.get("exp")

        user_tenant_id = payload.get(
            "user_tenant_id"
        )

        if user_tenant_id is None:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
            )

        user_tenant = (
            db.query(UserTenantDB)
            .join(
                TenantDB,
                UserTenantDB.tenant_id == TenantDB.id,
            )
            .filter(
                UserTenantDB.id == user_tenant_id,
                UserTenantDB.status == 1,
                TenantDB.status == 1,
            )
            .first()
        )

        if user_tenant is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        now = int(
            datetime.now(
                timezone.utc
            ).timestamp()
        )

        remaining_seconds = (
            exp - now
            if exp
            else None
        )

        return {
            "valid": True,
            "expiration": exp,
            "now": now,
            "remaining_seconds": remaining_seconds,
            "remaining_minutes_rounded": (
                math.ceil(
                    remaining_seconds / 60
                )
                if remaining_seconds is not None
                else None
            ),
            "user": {
                "dni": user_tenant.user.dni,
                "email": user_tenant.email,
            },
            "tenant": {
                "id": user_tenant.tenant.id,
                "slug": user_tenant.tenant.slug,
            },
            "user_tenant_id": user_tenant.id,
        }

    except HTTPException:
        raise

    except JWTError as exc:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        ) from exc
