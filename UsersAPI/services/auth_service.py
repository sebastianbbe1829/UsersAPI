import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import set_rls_tenant
from ..logging_config import logger
from ..models import TenantConfigDB, UserTenantDB, TenantDB
from ..schemas import LoginRequest
from .account_lock_notification_service import notify_tenant_admins_account_locked
from .auth_audit_service import ACCOUNT_LOCKED, LOGIN_FAILED, audit_auth_event
from .auth_context_service import get_current_user_from_token
from .authorization_service import get_user_permissions, user_can_authenticate
from .jwt_service import create_access_token
from .password_service import verify_password

AUTH_SCHEME = "bearer"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
LOCKED_ACCOUNT_MESSAGE = "Cuenta bloqueada, comuníquese con el administrador"


@dataclass(frozen=True)
class LoginFailure:
    status_code: int
    detail: str


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_max_login_attempts(db: Session, tenant_id: int) -> int:
    config = (
        db.query(TenantConfigDB)
        .filter(TenantConfigDB.tenant_id == tenant_id)
        .first()
    )
    if config is None or config.max_login_attempts is None:
        return 0
    return max(0, int(config.max_login_attempts))


def _register_failed_login(
    db: Session,
    user_tenant: UserTenantDB,
    *,
    client_ip: str | None,
    user_agent: str | None,
    max_login_attempts: int,
) -> bool:
    now = _now()
    user_tenant.failed_login_attempts = (user_tenant.failed_login_attempts or 0) + 1
    user_tenant.last_failed_login_at = now

    audit_auth_event(
        db,
        tenant_id=user_tenant.tenant_id,
        event_type=LOGIN_FAILED,
        user_tenant=user_tenant,
        client_ip=client_ip,
        user_agent=user_agent,
    )

    if max_login_attempts <= 0 or user_tenant.failed_login_attempts < max_login_attempts:
        return False

    if user_tenant.locked_at is None:
        user_tenant.locked_at = now
        user_tenant.locked_ip = client_ip
        audit_auth_event(
            db,
            tenant_id=user_tenant.tenant_id,
            event_type=ACCOUNT_LOCKED,
            user_tenant=user_tenant,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        return True

    return False


def login_user(
    datos: LoginRequest,
    db: Session,
    client_ip: str | None = None,
    user_agent: str | None = None,
):
    logger.info("Intento login usuario=%s tenant=%s", datos.username, datos.tenant)

    tenant_id = db.execute(
        text("SELECT users_api.resolve_tenant_id(:tenant_slug)"),
        {"tenant_slug": datos.tenant},
    ).scalar()

    if tenant_id is None:
        logger.warning("Tenant no encontrado slug=%s", datos.tenant)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant inválido")

    tenant_id = int(tenant_id)
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
        .with_for_update()
        .first()
    )

    if user_tenant is None:
        logger.warning(
            "Usuario no encontrado en tenant email=%s tenant_id=%s",
            datos.username,
            tenant_id,
        )
        audit_auth_event(
            db,
            tenant_id=tenant_id,
            event_type=LOGIN_FAILED,
            actor_login=datos.username,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        return LoginFailure(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credenciales inválidas o usuario inactivo",
        )

    max_login_attempts = _get_max_login_attempts(db, tenant_id)

    if user_tenant.locked_at is not None:
        logger.warning(
            "Intento de acceso a cuenta bloqueada user_tenant_id=%s tenant_id=%s",
            user_tenant.id,
            tenant_id,
        )
        audit_auth_event(
            db,
            tenant_id=tenant_id,
            event_type=LOGIN_FAILED,
            user_tenant=user_tenant,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        return LoginFailure(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=LOCKED_ACCOUNT_MESSAGE,
        )

    if not verify_password(datos.password, user_tenant.password):
        locked_now = _register_failed_login(
            db,
            user_tenant,
            client_ip=client_ip,
            user_agent=user_agent,
            max_login_attempts=max_login_attempts,
        )
        logger.warning(
            "Password inválido usuario=%s tenant_id=%s failed_attempts=%s",
            datos.username,
            tenant_id,
            user_tenant.failed_login_attempts,
        )

        if locked_now:
            try:
                notify_tenant_admins_account_locked(
                    db,
                    tenant_id=tenant_id,
                    tenant_name=user_tenant.tenant.name,
                    user_name=user_tenant.user.name,
                    user_login=user_tenant.email,
                    failed_attempts=user_tenant.failed_login_attempts,
                )
            except Exception:
                logger.exception(
                    "Unexpected error notifying tenant admins about account lock user_tenant_id=%s",
                    user_tenant.id,
                )
            return LoginFailure(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=LOCKED_ACCOUNT_MESSAGE,
            )

        return LoginFailure(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credenciales inválidas",
        )

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

    # Un login correcto reinicia la racha de intentos fallidos.
    user_tenant.failed_login_attempts = 0
    user_tenant.last_failed_login_at = None

    tenant = user_tenant.tenant
    usuario = user_tenant.user
    permissions = get_user_permissions(user_tenant=user_tenant, db=db)
    session_id = str(uuid.uuid4())

    access_token = create_access_token(
        {
            "sub": usuario.dni,
            "name": usuario.name,
            "email": user_tenant.email,
            "tenant_id": tenant.id,
            "tenant_slug": tenant.slug,
            "user_tenant_id": user_tenant.id,
            "permissions": permissions,
            "session_id": session_id,
        }
    )

    logger.info(
        "Login exitoso usuario=%s tenant=%s permisos=%s",
        datos.username,
        tenant.slug,
        len(permissions),
    )

    return {"access_token": access_token, "token_type": AUTH_SCHEME}


def get_current_user(token: str, db: Session) -> UserTenantDB:
    """Backward-compatible public API delegating tenant JWT context resolution."""
    return get_current_user_from_token(token, db)


def get_current_user_tenant(token: str, db: Session) -> UserTenantDB:
    return get_current_user(token, db)
