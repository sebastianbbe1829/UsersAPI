from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import RoleDB, UserTenantDB, UserTenantRoleDB
from ..util.email_utils import send_email

ADMIN_ROLE_CODES = ("ADMIN",)


def _get_admin_recipients(db: Session, tenant_id: int) -> list[str]:
    statement = (
        select(UserTenantDB.email)
        .join(UserTenantRoleDB, UserTenantRoleDB.user_tenant_id == UserTenantDB.id)
        .join(RoleDB, RoleDB.id == UserTenantRoleDB.role_id)
        .where(
            and_(
                UserTenantDB.tenant_id == tenant_id,
                UserTenantDB.status == 1,
                RoleDB.tenant_id == tenant_id,
                RoleDB.code.in_(ADMIN_ROLE_CODES),
                RoleDB.status == 1,
            )
        )
        .distinct()
    )
    rows = db.execute(statement).scalars().all()
    return [email.strip() for email in rows if email and email.strip()]


def notify_tenant_admins_account_locked(
    db: Session,
    *,
    tenant_id: int,
    tenant_name: str,
    user_name: str,
    user_login: str,
    failed_attempts: int,
) -> None:
    """Notifica a los administradores del tenant sin exponer credenciales."""
    recipients = _get_admin_recipients(db, tenant_id)
    if not recipients:
        logger.warning(
            "No active ADMIN email found for locked account tenant_id=%s",
            tenant_id,
        )
        return

    subject = f"Cuenta bloqueada por intentos fallidos - {tenant_name}"
    message = (
        f"Usuario {user_name} ({user_login}) bloqueado después de "
        f"{failed_attempts} intentos fallidos de autenticación.\n\n"
        "Este es un mensaje automático del sistema."
    )

    for recipient in recipients:
        try:
            send_email(
                recipient=recipient,
                subject=subject,
                message=message,
                tenant_name=tenant_name,
                template="default",
            )
        except Exception:
            logger.exception(
                "Error sending account lock notification to %s for tenant_id=%s",
                recipient,
                tenant_id,
            )
