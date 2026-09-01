from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import set_rls_tenant
from ..logging_config import logger
from ..models import TenantDB, UserTenantDB
from ..repositories.user_tenant_repository import UserTenantRepository
from ..settings import settings
from .auth_service import get_password_hash
from .otp_service import generate_otp, validate_otp

PASSWORD_RECOVERY_PURPOSE = "PASSWORD_RECOVERY"


def _resolve_tenant(tenant_slug: str, db: Session) -> int:
    tenant_id = db.execute(
        text("SELECT users_api.resolve_tenant_id(:tenant_slug)"),
        {"tenant_slug": tenant_slug.strip().lower()},
    ).scalar()

    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant inválido",
        )

    set_rls_tenant(db, tenant_id)
    return tenant_id


def request_password_recovery(
    *,
    tenant_slug: str,
    email: str,
    db: Session,
):
    """Solicita un OTP sin revelar si el correo existe en el tenant."""
    tenant_id = _resolve_tenant(tenant_slug, db)
    email = email.strip().lower()

    user_tenant = (
        db.query(UserTenantDB)
        .join(TenantDB, UserTenantDB.tenant_id == TenantDB.id)
        .filter(
            UserTenantDB.email == email,
            UserTenantDB.tenant_id == tenant_id,
            UserTenantDB.status == 1,
            TenantDB.status == 1,
        )
        .first()
    )

    if user_tenant is None:
        logger.info(
            "Solicitud de recuperación para usuario no encontrado "
            "tenant_id=%s email=%s",
            tenant_id,
            email,
        )
        # Mantiene la misma forma de respuesta sin generar ni enviar un OTP.
        return datetime.utcnow() + timedelta(minutes=settings.otp_expire_minutes)

    return generate_otp(
        db,
        destination=email,
        purpose=PASSWORD_RECOVERY_PURPOSE,
        subject="Recuperación de contraseña",
        message="Hemos generado un código para recuperar tu contraseña.",
    )


def reset_password(
    *,
    tenant_slug: str,
    email: str,
    code: str,
    new_password: str,
    db: Session,
):
    """Valida el OTP y cambia la contraseña dentro de la misma transacción."""
    tenant_id = _resolve_tenant(tenant_slug, db)
    email = email.strip().lower()

    user_tenant = (
        db.query(UserTenantDB)
        .join(TenantDB, UserTenantDB.tenant_id == TenantDB.id)
        .filter(
            UserTenantDB.email == email,
            UserTenantDB.tenant_id == tenant_id,
            UserTenantDB.status == 1,
            TenantDB.status == 1,
        )
        .first()
    )

    if user_tenant is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido o expirado.",
        )

    otp_valid = validate_otp(
        db,
        destination=email,
        purpose=PASSWORD_RECOVERY_PURPOSE,
        code=code,
    )

    if not otp_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido o expirado.",
        )

    user_tenant.password = get_password_hash(new_password)
    user_tenant.updated_at = datetime.now()
    user_tenant.updated_by = "PASSWORD_RECOVERY"

    UserTenantRepository(db).update(user_tenant)

    logger.info(
        "Contraseña actualizada mediante recuperación "
        "user_tenant_id=%s tenant_id=%s",
        user_tenant.id,
        tenant_id,
    )

    return {"message": "Contraseña actualizada correctamente."}
