from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import GlobalUserDB, UserTenantDB
from ..repositories.user_repository import UserRepository
from ..repositories.user_tenant_repository import UserTenantRepository
from ..repositories.tenant_repository import TenantRepository
from ..schemas import UserUpdate
from ..util.email_utils import send_email
from ..util.whatsapp_utils import send_whatsapp
from .auth_audit_service import audit_auth_event
from .password_service import get_password_hash
from .user_service_helpers import _actor_dni, _get_user_entity, _tenant_link, _user_payload

ACCOUNT_UNLOCKED = "ACCOUNT_UNLOCKED"


def update_user(
    dni: str,
    datos: UserUpdate,
    db: Session,
    current_user: UserTenantDB | GlobalUserDB,
    user_tenant: UserTenantDB,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    tenant_repository = TenantRepository(db)

    tenant_id = user_tenant.tenant_id

    tenant = tenant_repository.get_by_id(
        tenant_id=tenant_id
    )

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )

    tenant_slug = tenant.slug
    tenant_name = tenant.name

    usuario = _get_user_entity(dni, tenant_id, user_repository)
    link = _tenant_link(usuario, tenant_id, user_tenant_repository)

    cambios = datos.model_dump(exclude_unset=True)
    desbloquear = cambios.pop("unlock", False) is True

    if desbloquear:
        if link.locked_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La cuenta no se encuentra bloqueada",
            )

        ahora = datetime.now()
        actor = _actor_dni(current_user)
        actor_login = (
            current_user.email
            if isinstance(current_user, UserTenantDB)
            else current_user.email
        )

        link.failed_login_attempts = 0
        link.last_failed_login_at = None
        link.locked_at = None
        link.locked_ip = None
        link.updated_at = ahora
        link.updated_by = actor

        audit_auth_event(
            db,
            tenant_id=tenant_id,
            event_type=ACCOUNT_UNLOCKED,
            user_tenant_id=link.id,
            # user_tenant.user_id references app_users, not global_users.
            global_user_id=None,
            actor_dni=actor,
            actor_login=actor_login,
        )

    if "name" in cambios:
        usuario.name = cambios["name"]

    for campo in ("email", "phone", "status"):
        if campo in cambios:
            setattr(link, campo, cambios[campo])

    if cambios.get("password") is not None:
        link.password = get_password_hash(cambios["password"])

    ahora = datetime.now()
    actor = _actor_dni(current_user)
    usuario.updated_at = ahora
    usuario.updated_by = actor
    link.updated_at = ahora
    link.updated_by = actor

    try:
        user_repository.update(usuario)
        user_tenant_repository.update(link)
    except IntegrityError as exc:
        logger.exception(
            "Error de integridad al actualizar usuario",
            extra={
                "dni": dni,
                "tenant_id": tenant_id,
                "email": link.email,
                "error": str(exc),
                "orig": str(exc.orig),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe o el email ya está registrado",
        ) from exc
    except Exception as exc:
        logger.exception(
            "Error al actualizar usuario",
            extra={"dni": dni, "tenant_id": tenant_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar usuario",
        ) from exc

    if desbloquear and not cambios:
        return _user_payload(
            usuario,
            link,
            message="Cuenta desbloqueada correctamente",
        )

    try:
        send_email(
            recipient=link.email,
            subject=f"Tu cuenta en {tenant_name} fue actualizada",
            message=(
                f"Hola {usuario.name}, "
                f"la información de tu cuenta en {tenant_name} ha sido actualizada."
            ),
            tenant_slug=tenant_slug,
            tenant_name=tenant_name,
            template="updated",
        )
    except Exception as exc:
        logger.warning(
            "Usuario actualizado pero falló el envío de correo: %s",
            exc,
        )

    try:
        if link.phone:
            send_whatsapp(
                to_number=link.phone,
                message=(
                    f"Hola {usuario.name}, "
                    "tu cuenta ha sido actualizada exitosamente."
                ),
                template_name="hello_world",
                parameters=None,
            )
    except Exception as exc:
        logger.warning(
            "Usuario actualizado pero falló el envío de WhatsApp: %s",
            exc,
        )

    return _user_payload(usuario, link)
