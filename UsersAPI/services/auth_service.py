import math

from datetime import datetime, timezone

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import set_rls_tenant
from ..logging_config import logger
from ..models import UserTenantDB, TenantDB
from ..schemas import LoginRequest
from .auth_context_service import get_current_user_from_token
from .authorization_service import get_user_permissions, user_can_authenticate
from .jwt_service import ALGORITHM, SECRET_KEY, create_access_token
from .password_service import get_password_hash, pwd_context, verify_password


# ============================================================
# CONFIGURACIÓN
# ============================================================

AUTH_SCHEME = "bearer"

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/login",
)


# ============================================================
# LOGIN MULTI-TENANT
# ============================================================


def login_user(
    datos: LoginRequest,
    db: Session,
):

    logger.info("Intento login usuario=%s tenant=%s", datos.username, datos.tenant)

    tenant_id = db.execute(
        text("""
            SELECT users_api.resolve_tenant_id(:tenant_slug)
            """),
        {"tenant_slug": datos.tenant},
    ).scalar()

    if tenant_id is None:
        logger.warning("Tenant no encontrado slug=%s", datos.tenant)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant inválido")

    logger.info("Tenant resuelto slug=%s tenant_id=%s", datos.tenant, tenant_id)

    set_rls_tenant(db, tenant_id)
    logger.info("Contexto RLS establecido tenant_id=%s", tenant_id)

    user_tenant = (
        db.query(UserTenantDB)
        .join(TenantDB, UserTenantDB.tenant_id == TenantDB.id)
        .filter(
            UserTenantDB.email == datos.username,
            UserTenantDB.tenant_id == tenant_id,
            UserTenantDB.status == 1,
            TenantDB.status == 1,
        )
        .first()
    )

    if user_tenant is None:
        logger.warning("Usuario no encontrado en tenant email=%s tenant_id=%s", datos.username, tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credenciales inválidas o usuario inactivo",
        )

    if not verify_password(datos.password, user_tenant.password):
        logger.warning("Password inválido usuario=%s", datos.username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Credenciales inválidas")

    if not user_can_authenticate(user_tenant=user_tenant, db=db):
        logger.warning(
            "Usuario sin permiso AUTHENTICATE user_tenant_id=%s tenant_id=%s",
            user_tenant.id,
            user_tenant.tenant_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene permiso para autenticarse",
        )

    tenant = user_tenant.tenant
    usuario = user_tenant.user
    permissions = get_user_permissions(user_tenant=user_tenant, db=db)

    access_token = create_access_token({
        "sub": usuario.dni,
        "name": usuario.name,
        "tenant_id": tenant.id,
        "tenant_slug": tenant.slug,
        "user_tenant_id": user_tenant.id,
        "permissions": permissions,
    })

    logger.info(
        "Login exitoso usuario=%s tenant=%s permisos=%s",
        datos.username,
        tenant.slug,
        len(permissions),
    )

    return {"access_token": access_token, "token_type": AUTH_SCHEME}


# ============================================================
# CURRENT USER
# ============================================================


def get_current_user(token: str, db: Session) -> UserTenantDB:
    """Backward-compatible public API delegating tenant JWT context resolution."""
    return get_current_user_from_token(token, db)


# ============================================================
# CURRENT USER TENANT
# ============================================================


def get_current_user_tenant(token: str, db: Session) -> UserTenantDB:
    return get_current_user(token, db)


# ============================================================
# VALIDATE TOKEN
# ============================================================


def validate_token(token: str, db: Session):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )

        exp = payload.get("exp")
        user_tenant_id = payload.get("user_tenant_id")

        if user_tenant_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

        token_tenant_id = payload.get("tenant_id")
        if token_tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token sin tenant asociado",
            )

        set_rls_tenant(db, token_tenant_id)

        user_tenant = (
            db.query(UserTenantDB)
            .join(TenantDB, UserTenantDB.tenant_id == TenantDB.id)
            .filter(
                UserTenantDB.id == user_tenant_id,
                UserTenantDB.status == 1,
                TenantDB.status == 1,
            )
            .first()
        )

        if user_tenant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

        if user_tenant.tenant_id != token_tenant_id:
            logger.warning(
                "Inconsistencia tenant JWT usuario_tenant=%s token_tenant=%s",
                user_tenant.tenant_id,
                token_tenant_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="El tenant del token no coincide con el usuario",
            )

        now = int(datetime.now(timezone.utc).timestamp())
        remaining_seconds = exp - now if exp else None

        return {
            "valid": True,
            "expiration": exp,
            "now": now,
            "remaining_seconds": remaining_seconds,
            "remaining_minutes_rounded": (
                math.ceil(remaining_seconds / 60) if remaining_seconds is not None else None
            ),
            "user": {"dni": user_tenant.user.dni, "email": user_tenant.email},
            "tenant": {"id": user_tenant.tenant.id, "slug": user_tenant.tenant.slug},
            "user_tenant_id": user_tenant.id,
        }

    except HTTPException:
        raise
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        ) from exc
