import base64
import hashlib
import hmac
import uuid
from datetime import datetime, timezone

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status
from jose import JWTError, ExpiredSignatureError, jwt
from sqlalchemy.orm import Session

from ..database import set_rls_tenant
from ..logging_config import logger
from ..models import GlobalUserDB, TenantDB
from ..schemas.global_auth import (
    SuperBootstrapRequest,
    SuperBootstrapResponse,
    SuperLoginRequest,
    SuperLoginResponse,
)
from ..services.auth_service import get_password_hash, verify_password
from ..settings import settings


SUPER_TOKEN_TYPE = "SUPER"


def _fernet() -> Fernet:
    key = settings.super_mfa_encryption_key

    if not key:
        key = base64.urlsafe_b64encode(
            hashlib.sha256(
                settings.secret_key.encode("utf-8")
            ).digest()
        ).decode("ascii")

    try:
        return Fernet(key.encode("ascii"))
    except Exception as exc:
        raise RuntimeError(
            "SUPER_MFA_ENCRYPTION_KEY no contiene una clave Fernet válida"
        ) from exc


def _encrypt_mfa_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode("utf-8")).decode("ascii")


def _decrypt_mfa_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible validar la configuración MFA",
        ) from exc


def _create_super_token(
    user: GlobalUserDB,
    tenant: TenantDB,
) -> str:
    now = datetime.now(timezone.utc)
    exp = now.timestamp() + settings.access_token_expire_minutes * 60

    payload = {
        "sub": str(user.id),
        "name": user.email,
        "email": user.email,
        "global_user_id": user.id,
        "user_type": SUPER_TOKEN_TYPE,
        "session_id": user.session_id,
        "tenant_id": tenant.id,
        "tenant_slug": tenant.slug,
        "iat": int(now.timestamp()),
        "exp": int(exp),
    }

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def bootstrap_super_user(
    datos: SuperBootstrapRequest,
    bootstrap_secret: str,
    db: Session,
) -> SuperBootstrapResponse:

    if not settings.super_bootstrap_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El bootstrap del usuario SUPER no está configurado",
        )

    if not hmac.compare_digest(
        bootstrap_secret,
        settings.super_bootstrap_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Secret de bootstrap inválida",
        )

    existing = (
        db.query(GlobalUserDB)
        .filter(GlobalUserDB.is_superuser.is_(True))
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Ya existe al menos un usuario SUPER; "
                "utilice la administración de usuarios globales"
            ),
        )

    email = datos.email.strip().lower()

    if (
        db.query(GlobalUserDB)
        .filter(GlobalUserDB.email == email)
        .first()
        is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya está registrado como usuario global",
        )

    secret = pyotp.random_base32()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    user = GlobalUserDB(
        email=email,
        password_hash=get_password_hash(datos.password),
        is_active=True,
        is_superuser=True,
        mfa_enabled=True,
        mfa_secret_encrypted=_encrypt_mfa_secret(secret),
        session_id=None,
        created_at=now,
        created_by="super-bootstrap",
        updated_at=now,
        updated_by="super-bootstrap",
    )

    db.add(user)
    db.flush()

    provisioning_uri = pyotp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name="UsersAPI",
    )

    logger.info(
        "Usuario SUPER creado correctamente email=%s",
        email,
    )

    return SuperBootstrapResponse(
        id=user.id,
        email=user.email,
        mfa_enabled=True,
        provisioning_uri=provisioning_uri,
    )


def login_super_user(
    datos: SuperLoginRequest,
    db: Session,
    client_ip: str | None = None,
) -> SuperLoginResponse:

    email = datos.email.strip().lower()
    tenant_slug = datos.tenant.strip().lower()

    tenant = (
        db.query(TenantDB)
        .filter(
            TenantDB.slug == tenant_slug,
            TenantDB.status == 1,
        )
        .first()
    )

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado o inactivo",
        )

    user = (
        db.query(GlobalUserDB)
        .filter(GlobalUserDB.email == email)
        .first()
    )

    if user is None or not user.is_active or not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(datos.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.mfa_enabled:
        if not datos.otp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Código MFA requerido",
            )

        if not user.mfa_secret_encrypted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="El usuario SUPER no tiene MFA configurado",
            )

        secret = _decrypt_mfa_secret(user.mfa_secret_encrypted)

        if not pyotp.TOTP(secret).verify(datos.otp, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Código MFA inválido",
            )

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    user.session_id = str(uuid.uuid4())
    user.last_login_at = now
    user.last_login_ip = client_ip
    user.updated_at = now
    user.updated_by = "super-login"

    db.add(user)
    db.flush()

    token = _create_super_token(user, tenant)

    # El SUPER trabaja sobre el tenant seleccionado durante el login.
    # A partir de aquí las consultas protegidas por RLS deben operar
    # sobre ese tenant, igual que una sesión normal.
    set_rls_tenant(
        db,
        tenant.id,
    )

    logger.info(
        "Login SUPER exitoso email=%s tenant=%s session_id=%s",
        user.email,
        tenant.slug,
        user.session_id,
    )

    return SuperLoginResponse(
        access_token=token,
        token_type="bearer",
        user_type=SUPER_TOKEN_TYPE,
        session_id=user.session_id,
        tenant_id=tenant.id,
        tenant_slug=tenant.slug,
    )


def get_current_super_user(
    token: str,
    db: Session,
) -> GlobalUserDB:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token SUPER",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token SUPER expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except JWTError as exc:
        raise credentials_exception from exc

    if payload.get("user_type") != SUPER_TOKEN_TYPE:
        raise credentials_exception

    global_user_id = payload.get("global_user_id")
    session_id = payload.get("session_id")
    tenant_id = payload.get("tenant_id")
    tenant_slug = payload.get("tenant_slug")

    if (
        global_user_id is None
        or session_id is None
        or tenant_id is None
        or tenant_slug is None
    ):
        raise credentials_exception

    user = (
        db.query(GlobalUserDB)
        .filter(
            GlobalUserDB.id == global_user_id,
            GlobalUserDB.is_active.is_(True),
            GlobalUserDB.is_superuser.is_(True),
        )
        .first()
    )

    if user is None or user.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión SUPER ya no es válida",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tenant = (
        db.query(TenantDB)
        .filter(
            TenantDB.id == tenant_id,
            TenantDB.slug == tenant_slug,
            TenantDB.status == 1,
        )
        .first()
    )

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El tenant asociado a la sesión SUPER ya no es válido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Cada request SUPER vuelve a establecer el contexto RLS del tenant
    # seleccionado en el JWT.
    set_rls_tenant(
        db,
        tenant.id,
    )

    return user
