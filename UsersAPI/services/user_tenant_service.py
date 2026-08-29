import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import UserDB, UserTenantDB
from ..repositories.tenant_repository import TenantRepository
from ..repositories.user_repository import UserRepository
from ..repositories.user_tenant_repository import UserTenantRepository
from .auth_service import get_password_hash

from ..util.email_utils import send_email
from ..util.whatsapp_utils import send_whatsapp


# ============================================================
# UTILIDADES
# ============================================================

def _actor_dni(
    current_user: UserDB | UserTenantDB | None,
) -> str:

    if current_user is None:
        return "bootstrap"

    if isinstance(current_user, UserTenantDB):
        return current_user.user.dni

    return current_user.dni


def _generate_activation_token() -> str:
    return str(uuid.uuid4())


# ============================================================
# NOTIFICACIÓN DE BIENVENIDA
# ============================================================

def _send_welcome_notifications(
    user: UserDB,
    user_tenant: UserTenantDB,
    reactivated: bool = False,
):

    """
    Envía correo y WhatsApp.

    IMPORTANTE:
    Si falla una notificación NO se revierte
    la creación/reactivación del usuario.
    """

    if reactivated:
        email_subject = "Bienvenido nuevamente a UsersAPI"
        email_message = (
            f"Hola {user.name}, "
            f"tu cuenta ha sido reactivada exitosamente."
        )
    else:
        email_subject = "Bienvenido a UsersAPI"
        email_message = (
            f"Hola {user.name}, "
            f"tu cuenta ha sido creada exitosamente."
        )

    tenant_id = user_tenant.tenant_id
    tenant_repository = TenantRepository()

    tenant = tenant_repository.get_by_id(
        tenant_id=tenant_id
    )
    tenant_slug = tenant.slug
    tenant_name = tenant.name

    try:
        send_email(
            recipient=user_tenant.email,
            subject=email_subject,
            message=email_message,
            dni=user.dni,
            token=user_tenant.activation_token,
            tenant_slug=tenant_slug,
            tenant_name=tenant_name,
        )

        logger.info(
            "Correo de bienvenida enviado",
            extra={
                "user_id": user.id,
                "user_tenant_id": user_tenant.id,
                "dni": user.dni,
                "email": user_tenant.email,
            },
        )

    except Exception as exc:
        logger.warning(
            "Usuario creado/reactivado pero falló el envío de correo: %s",
            exc,
        )

    if not user_tenant.phone:
        logger.info(
            "Usuario sin teléfono. Se omite envío de WhatsApp.",
            extra={
                "user_id": user.id,
                "user_tenant_id": user_tenant.id,
                "dni": user.dni,
            },
        )
        return

    try:
        send_whatsapp(
            to_number=user_tenant.phone,
            message=(
                f"Hola {user.name}, "
                f"tu cuenta en UsersAPI ha sido creada exitosamente."
            ),
            template_name="hello_world",
            parameters=None,
        )

        logger.info(
            "WhatsApp de bienvenida enviado",
            extra={
                "user_id": user.id,
                "user_tenant_id": user_tenant.id,
                "dni": user.dni,
            },
        )

    except Exception as exc:
        logger.warning(
            "Usuario creado/reactivado pero falló el envío de WhatsApp: %s",
            exc,
        )
