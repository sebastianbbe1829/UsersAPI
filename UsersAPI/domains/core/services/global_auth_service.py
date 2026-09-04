import base64
import hashlib
import hmac
import uuid
from datetime import datetime, timezone

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import set_rls_tenant
from ..logging_config import logger
from ..models import GlobalUserDB, TenantDB
from ..schemas.global_auth import (
    SuperBootstrapMfaVerifyRequest,
    SuperBootstrapMfaVerifyResponse,
    SuperBootstrapRequest,
    SuperBootstrapResponse,
    SuperLoginRequest,
    SuperLoginResponse,
)
from ..services.jwt_service import create_access_token
from ..services.password_service import get_password_hash, verify_password
from ..settings import settings


SUPER_SESSION_KIND = "SUPER"
AUTH_SCHEME = "bearer"


def _fernet() -> Fernet:
    key = settings.super_mfa_encryption_key
    if not key:
        key = base64.urlsafe_b64encode(
            hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
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


def _validate_bootstrap_secret(bootstrap_secret: str) -> None:
    if not settings.super_bootstrap_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El bootstrap del usuario SUPER no está configurado",
        )
    if not hmac.compare_digest(bootstrap_secret, settings.super_bootstrap_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Secret de bootstrap inválida",
        )


def _create_super_token(user: GlobalUserDB, tenant: TenantDB) -> str:
    payload = {
        "sub": str(user.id),
        "name": user.name or user.email,
        "email": user.email,
        "global_user_id": user.id,
        "user_type": SUPER_SESSION_KIND,
        "session_id": user.session_id,
        "tenant_id": tenant.id,
        "tenant_slug": tenant.slug,
    }
    return create_access_token(payload)


def bootstrap_super_user(
    datos: SuperBootstrapRequest,
    bootstrap_secret: str,
    db: Session,
) -> SuperBootstrapResponse:
    _validate_bootstrap_secret(bootstrap_secret)
    existing = (
        db.query(GlobalUserDB)
        .filter(GlobalUserDB.is_superuser.is_(True))
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Ya existe al menos un usuario SUPER; utilice la "
                "administración de usuarios globales"
            ),
        )

    email = datos.email.strip().lower()
    dni = datos.dni.strip()
    if db.query(GlobalUserDB).filter(GlobalUserDB.email == email).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya está registrado como usuario global",
        )
    if db.query(GlobalUserDB).filter(GlobalUserDB.dni == dni).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El DNI ya está registrado como usuario SUPER",
        )

    secret = pyotp.random_base32()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user = GlobalUserDB(
        dni=dni,
        name=datos.name.strip(),
        phone=datos.phone.strip(),
        email=email,
        password_hash=get_password_hash(datos.password),
        is_active=True,
        is_superuser=True,
        mfa_enabled=True,
        mfa_secret_encrypted=_encrypt_mfa_secret(secret),
        mfa_verified_at=None,
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
    logger.info("Usuario SUPER creado correctamente email=%s", email)
    return SuperBootstrapResponse(
        id=user.id,
        dni=user.dni,
        name=user.name,
        phone=user.phone,
        email=user.email,
        mfa_enabled=True,
        provisioning_uri=provisioning_uri,
    )


def verify_bootstrap_mfa(
    datos: SuperBootstrapMfaVerifyRequest,
    bootstrap_secret: str,
    db: Session,
) -> SuperBootstrapMfaVerifyResponse:
    _validate_bootstrap_secret(bootstrap_secret)
    user = (
        db.query(GlobalUserDB)
        .filter(
            GlobalUserDB.id == datos.user_id,
            GlobalUserDB.is_active.is_(True),
            GlobalUserDB.is_superuser.is_(True),
        )
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario SUPER no encontrado",
        )
    if user.mfa_verified_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El MFA del usuario SUPER ya fue verificado",
        )
    if not user.mfa_enabled or not user.mfa_secret_encrypted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario SUPER no tiene un enrolamiento MFA pendiente",
        )
    secret = _decrypt_mfa_secret(user.mfa_secret_encrypted)
    if not pyotp.TOTP(secret).verify(datos.otp, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código MFA inválido",
        )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user.mfa_verified_at = now
    user.updated_at = now
    user.updated_by = "super-bootstrap-mfa"
    db.add(user)
    db.flush()
    return SuperBootstrapMfaVerifyResponse(
        id=user.id,
        email=user.email,
        mfa_enabled=user.mfa_enabled,
        mfa_verified=True,
    )


def login_super_user(
    datos: SuperLoginRequest,
    db: Session,
    client_ip: str | None = None,
) -> SuperLoginResponse:
    email = datos.email.strip().lower()
    tenant_slug = datos.tenant.strip().lower()
    tenant_id = db.execute(
        text("SELECT users_api.resolve_tenant_id(:tenant_slug)"),
        {"tenant_slug": tenant_slug},
    ).scalar()
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado o inactivo",
        )
    set_rls_tenant(db, tenant_id)
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado o inactivo",
        )
    user = db.query(GlobalUserDB).filter(GlobalUserDB.email == email).first()
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
        if not user.mfa_secret_encrypted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="El usuario SUPER no tiene MFA configurado",
            )
        if not datos.otp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    "Código MFA requerido. Si es el primer ingreso, "
                    "configure el MFA con el QR entregado por el administrador."
                ),
            )
        secret = _decrypt_mfa_secret(user.mfa_secret_encrypted)
        if not pyotp.TOTP(secret).verify(datos.otp, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Código MFA inválido",
            )
        if user.mfa_verified_at is None:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            user.mfa_verified_at = now
            user.updated_at = now
            user.updated_by = "super-first-login-mfa"
            db.add(user)
            db.flush()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user.session_id = str(uuid.uuid4())
    user.last_login_at = now
    user.last_login_ip = client_ip
    user.updated_at = now
    user.updated_by = "super-login"
    db.add(user)
    db.flush()
    token = _create_super_token(user, tenant)
    return SuperLoginResponse(
        access_token=token,
        token_type=AUTH_SCHEME,
        user_type=SUPER_SESSION_KIND,
        session_id=user.session_id,
        tenant_id=tenant.id,
        tenant_slug=tenant.slug,
    )


def get_current_super_user(token: str, db: Session) -> GlobalUserDB:
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
    if payload.get("user_type") != SUPER_SESSION_KIND:
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
    resolved_tenant_id = db.execute(
        text("SELECT users_api.resolve_tenant_id(:tenant_slug)"),
        {"tenant_slug": tenant_slug},
    ).scalar()
    if (
        resolved_tenant_id is None
        or int(resolved_tenant_id) != int(tenant_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El tenant asociado a la sesión SUPER ya no es válido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    set_rls_tenant(db, int(resolved_tenant_id))
    return user
