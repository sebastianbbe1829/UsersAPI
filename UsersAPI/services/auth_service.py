import math

from datetime import datetime, timedelta, timezone
from typing import Optional

from argon2 import PasswordHasher
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import set_rls_tenant
from ..logging_config import logger
from ..models import (
    UserTenantDB,
    TenantDB,
    UserTenantRoleDB,
    RoleDB,
    RolePermissionDB,
    PermissionDB,
)
from ..schemas import LoginRequest
from ..settings import settings


# ============================================================
# CONFIGURACIÓN
# ============================================================

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


# PasswordHasher de argon2-cffi reemplaza Passlib.
# Mantiene Argon2 como algoritmo de almacenamiento y verificación
# sin depender del módulo crypt eliminado de Python 3.13.
pwd_context = PasswordHasher()


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
            hashed_password,
            plain_password,
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
# VALIDAR PERMISO DE AUTENTICACIÓN
# ============================================================


def user_can_authenticate(
    user_tenant: UserTenantDB,
    db: Session,
) -> bool:

    permission = (
        db.query(PermissionDB)
        .join(
            RolePermissionDB,
            RolePermissionDB.permission_id == PermissionDB.id,
        )
        .join(
            RoleDB,
            RoleDB.id == RolePermissionDB.role_id,
        )
        .join(
            UserTenantRoleDB,
            UserTenantRoleDB.role_id == RoleDB.id,
        )
        .filter(
            UserTenantRoleDB.user_tenant_id == user_tenant.id,

            # El rol debe pertenecer al mismo tenant
            RoleDB.tenant_id == user_tenant.tenant_id,

            # El rol debe estar activo
            RoleDB.status == 1,

            # El permiso debe estar activo
            PermissionDB.status == 1,

            # Permiso requerido para generar JWT
            PermissionDB.code == "AUTHENTICATE",
        )
        .first()
    )

    return permission is not None


def get_user_permissions(
    user_tenant: UserTenantDB,
    db: Session,
) -> list[str]:

    permissions = (
        db.query(PermissionDB.code)
        .join(
            RolePermissionDB,
            RolePermissionDB.permission_id == PermissionDB.id,
        )
        .join(
            RoleDB,
            RoleDB.id == RolePermissionDB.role_id,
        )
        .join(
            UserTenantRoleDB,
            UserTenantRoleDB.role_id == RoleDB.id,
        )
        .filter(
            UserTenantRoleDB.user_tenant_id == user_tenant.id,
            RoleDB.tenant_id == user_tenant.tenant_id,
            RoleDB.status == 1,
            PermissionDB.status == 1,
        )
        .distinct()
        .order_by(PermissionDB.code)
        .all()
    )

    return [code for (code,) in permissions]


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

    # ========================================================
    # RESOLVER TENANT
    #
    # El login todavía NO tiene tenant_id.
    #
    # Se recibe el slug y se utiliza la función
    # SECURITY DEFINER para obtener el ID del tenant.
    # ========================================================

    tenant_id = db.execute(
        text(
            """
            SELECT users_api.resolve_tenant_id(:tenant_slug)
            """
        ),
        {
            "tenant_slug": datos.tenant,
        },
    ).scalar()

    if tenant_id is None:

        logger.warning(
            "Tenant no encontrado slug=%s",
            datos.tenant,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant inválido",
        )

    logger.info(
        "Tenant resuelto slug=%s tenant_id=%s",
        datos.tenant,
        tenant_id,
    )

    # ========================================================
    # ESTABLECER CONTEXTO RLS
    #
    # A partir de este momento las consultas normales de la
    # aplicación quedan limitadas al tenant resuelto.
    # ========================================================

    set_rls_tenant(
        db,
        tenant_id,
    )

    logger.info(
        "Contexto RLS establecido tenant_id=%s",
        tenant_id,
    )

    # ========================================================
    # BUSCAR USUARIO EN EL TENANT
    # ========================================================

    user_tenant = (
        db.query(UserTenantDB)
        .join(
            TenantDB,
            UserTenantDB.tenant_id == TenantDB.id,
        )
        .filter(
            # LOGIN SIEMPRE POR EMAIL
            UserTenantDB.email == datos.username,

            # Tenant resuelto anteriormente
            UserTenantDB.tenant_id == tenant_id,

            # Usuario dentro del tenant activo
            UserTenantDB.status == 1,

            # Tenant activo
            TenantDB.status == 1,
        )
        .first()
    )

    if user_tenant is None:

        logger.warning(
            "Usuario no encontrado en tenant "
            "email=%s tenant_id=%s",
            datos.username,
            tenant_id,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credenciales inválidas o usuario inactivo",
        )

    # ========================================================
    # VALIDAR PASSWORD
    # ========================================================

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

    # ========================================================
    # VALIDAR PERMISO AUTHENTICATE
    #
    # El usuario debe tener al menos un rol activo dentro
    # del tenant que tenga asignado el permiso AUTHENTICATE.
    #
    # Si no lo tiene:
    #   - NO se genera JWT
    #   - NO se permite iniciar sesión
    # ========================================================

    if not user_can_authenticate(
        user_tenant=user_tenant,
        db=db,
    ):

        logger.warning(
            "Usuario sin permiso AUTHENTICATE "
            "user_tenant_id=%s tenant_id=%s",
            user_tenant.id,
            user_tenant.tenant_id,
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene permiso para autenticarse",
        )

    # ========================================================
    # DATOS DEL TENANT Y USUARIO
    # ========================================================

    tenant = user_tenant.tenant
    usuario = user_tenant.user
    permissions = get_user_permissions(
        user_tenant=user_tenant,
        db=db,
    )

    # ========================================================
    # CREAR JWT
    # ========================================================

    access_token = create_access_token(
        {
            "sub": usuario.dni,
            "name": usuario.name,
            "tenant_id": tenant.id,
            "tenant_slug": tenant.slug,
            "user_tenant_id": user_tenant.id,
            "permissions": permissions,
        }
    )

    logger.info(
        "Login exitoso usuario=%s tenant=%s permisos=%s",
        datos.username,
        tenant.slug,
        len(permissions),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
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

    # ========================================================
    # OBTENER TENANT DEL TOKEN
    # ========================================================

    token_tenant_id = payload.get(
        "tenant_id"
    )

    if token_tenant_id is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin tenant asociado",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    # ========================================================
    # ESTABLECER CONTEXTO RLS
    # ========================================================

    set_rls_tenant(
        db,
        token_tenant_id,
    )

    # ========================================================
    # BUSCAR USER TENANT ACTIVO
    # ========================================================

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

    # ========================================================
    # VALIDAR COHERENCIA DEL TENANT DEL TOKEN
    # ========================================================

    if user_tenant.tenant_id != token_tenant_id:

        logger.warning(
            "Inconsistencia tenant JWT "
            "usuario_tenant=%s token_tenant=%s",
            user_tenant.tenant_id,
            token_tenant_id,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El tenant del token no coincide con el usuario",
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

        # ====================================================
        # OBTENER TENANT DEL TOKEN
        # ====================================================

        token_tenant_id = payload.get(
            "tenant_id"
        )

        if token_tenant_id is None:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token sin tenant asociado",
            )

        # ====================================================
        # ESTABLECER CONTEXTO RLS
        # ====================================================

        set_rls_tenant(
            db,
            token_tenant_id,
        )

        # ====================================================
        # BUSCAR USER TENANT ACTIVO
        # ====================================================

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

        # ====================================================
        # VALIDAR COHERENCIA DEL TENANT
        # ====================================================

        if user_tenant.tenant_id != token_tenant_id:

            logger.warning(
                "Inconsistencia tenant JWT "
                "usuario_tenant=%s token_tenant=%s",
                user_tenant.tenant_id,
                token_tenant_id,
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="El tenant del token no coincide con el usuario",
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
