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

        email_subject = (
            "Bienvenido nuevamente a UsersAPI"
        )

        email_message = (
            f"Hola {user.name}, "
            f"tu cuenta ha sido reactivada exitosamente."
        )

    else:

        email_subject = (
            "Bienvenido a UsersAPI"
        )

        email_message = (
            f"Hola {user.name}, "
            f"tu cuenta ha sido creada exitosamente."
        )

    # ========================================================
    # CORREO
    # ========================================================

    try:

        send_email(
            recipient=user_tenant.email,
            subject=email_subject,
            message=email_message,
            dni=user.dni,
            token=user_tenant.activation_token,
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
            "Usuario creado/reactivado pero falló "
            "el envío de correo: %s",
            exc,
        )

    # ========================================================
    # WHATSAPP
    # ========================================================

    if not user_tenant.phone:
        logger.info(
            "Usuario sin teléfono. "
            "Se omite envío de WhatsApp.",
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
                f"tu cuenta en UsersAPI "
                f"ha sido creada exitosamente."
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
                "phone": user_tenant.phone,
            },
        )

    except Exception as exc:

        logger.warning(
            "Usuario creado/reactivado pero falló "
            "el envío de WhatsApp: %s",
            exc,
        )


# ============================================================
# CREAR ASOCIACIÓN USUARIO - TENANT
# ============================================================

def create_user_tenant(
    user_id: int,
    tenant_id: int,
    email: str,
    password: str,
    phone: str | None,
    db: Session,
    current_user: UserDB | UserTenantDB | None = None,
) -> UserTenantDB:

    user_repository = UserRepository(db)
    tenant_repository = TenantRepository(db)
    user_tenant_repository = UserTenantRepository(db)

    actor = _actor_dni(current_user)

    # ========================================================
    # VALIDAR USUARIO
    # ========================================================

    usuario = user_repository.get_by_id_including_deleted(
        user_id
    )

    if usuario is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no existe",
        )

    # ========================================================
    # VALIDAR TENANT
    # ========================================================

    tenant = tenant_repository.get_by_id_including_deleted(
        tenant_id
    )

    if tenant is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El tenant no existe",
        )

    if tenant.status == 3:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tenant está eliminado",
        )

    if tenant.status != 1:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tenant está inactivo",
        )

    # ========================================================
    # VALIDAR ASOCIACIÓN EXISTENTE
    # ========================================================

    existente = (
        user_tenant_repository
        .get_by_user_and_tenant_including_deleted(
            user_id,
            tenant_id,
        )
    )

    # ========================================================
    # REACTIVAR
    # ========================================================

    if existente is not None:

        if existente.status == 3:

            existente.status = 1
            existente.email = email
            existente.password = get_password_hash(password)
            existente.phone = phone
            existente.activation_token = (
                _generate_activation_token()
            )
            existente.updated_at = datetime.now()
            existente.updated_by = actor

            user_tenant_repository.mark_dirty(
                existente
            )

            logger.info(
                "Asociación usuario-tenant reactivada",
                extra={
                    "user_tenant_id": existente.id,
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "dni": usuario.dni,
                },
            )

            _send_welcome_notifications(
                user=usuario,
                user_tenant=existente,
                reactivated=True,
            )

            return existente

        # ====================================================
        # YA EXISTE
        # ====================================================

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "El usuario ya está asociado "
                "a este tenant"
            ),
        )

    # ========================================================
    # CREAR NUEVA ASOCIACIÓN
    # ========================================================

    nueva_asociacion = UserTenantDB(
        user_id=user_id,
        tenant_id=tenant_id,
        email=email,
        password=get_password_hash(password),
        phone=phone,
        activation_token=_generate_activation_token(),
        status=1,
        created_at=datetime.now(),
        created_by=actor,
    )

    try:

        creada = (
            user_tenant_repository
            .add_without_commit(
                nueva_asociacion
            )
        )

    except IntegrityError as exc:

        logger.warning(
            "Intento de crear asociación duplicada",
            extra={
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "El usuario ya está asociado "
                "a este tenant"
            ),
        ) from exc

    logger.info(
        "Usuario asociado a tenant",
        extra={
            "user_tenant_id": creada.id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "dni": usuario.dni,
        },
    )

    _send_welcome_notifications(
        user=usuario,
        user_tenant=creada,
        reactivated=False,
    )

    return creada


# ============================================================
# OBTENER ASOCIACIÓN
# ============================================================

def get_user_tenant(
    user_tenant_id: int,
    db: Session,
) -> UserTenantDB:

    repository = UserTenantRepository(db)

    asociacion = repository.get_by_id(
        user_tenant_id
    )

    if asociacion is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Asociación usuario-tenant "
                "no encontrada"
            ),
        )

    return asociacion


# ============================================================
# LISTAR TENANTS DE UN USUARIO
# ============================================================

def list_user_tenants(
    user_id: int,
    db: Session,
):

    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)

    usuario = (
        user_repository
        .get_by_id_including_deleted(
            user_id
        )
    )

    if usuario is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no existe",
        )

    return user_tenant_repository.get_by_user(
        user_id
    )


# ============================================================
# LISTAR USUARIOS DE UN TENANT
# ============================================================

def list_tenant_users(
    tenant_id: int,
    db: Session,
):

    tenant_repository = TenantRepository(db)
    user_tenant_repository = UserTenantRepository(db)

    tenant = (
        tenant_repository
        .get_by_id_including_deleted(
            tenant_id
        )
    )

    if tenant is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El tenant no existe",
        )

    return user_tenant_repository.get_by_tenant(
        tenant_id
    )


# ============================================================
# ELIMINAR ASOCIACIÓN USUARIO - TENANT
# ============================================================

def delete_user_tenant(
    user_tenant_id: int,
    db: Session,
):

    repository = UserTenantRepository(db)

    asociacion = repository.get_by_id(
        user_tenant_id
    )

    if asociacion is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Asociación usuario-tenant "
                "no encontrada"
            ),
        )

    asociacion.status = 3
    asociacion.updated_at = datetime.now()

    repository.mark_dirty(
        asociacion
    )

    logger.info(
        "Asociación usuario-tenant eliminada",
        extra={
            "user_tenant_id": asociacion.id,
            "user_id": asociacion.user_id,
            "tenant_id": asociacion.tenant_id,
        },
    )

    return {
        "id": asociacion.id,
        "user_id": asociacion.user_id,
        "tenant_id": asociacion.tenant_id,
        "status": asociacion.status,
        "message": (
            "Asociación usuario-tenant "
            "eliminada correctamente"
        ),
    }