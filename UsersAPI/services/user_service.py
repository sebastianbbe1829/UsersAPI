from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import text

from UsersAPI.util.excel_utils import export_to_excel

from ..logging_config import logger
from ..models import GlobalUserDB, UserDB, UserTenantDB
from ..repositories.user_repository import UserRepository
from ..repositories.user_tenant_repository import UserTenantRepository
from ..schemas import UserCreate, UserUpdate
from ..util.email_utils import send_email
from ..util.whatsapp_utils import send_whatsapp
from ..repositories.tenant_repository import TenantRepository
from ..database import set_rls_tenant
from .user_creation_service import (
    create_global_user,
    create_tenant_link,
    reactivate_user,
)
from .user_service_helpers import (
    _actor_dni,
    _get_user_entity,
    _tenant_link,
    _user_payload,
)
from .user_update_service import update_user as _update_user


# ============================================================
# CREAR / REACTIVAR USUARIO
# ============================================================

def create_user(
    user: UserCreate,
    db: Session,
    current_user: UserTenantDB | GlobalUserDB | None = None,
    user_tenant: UserTenantDB | None = None,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    tenant_repository = TenantRepository(db)

    if user_tenant is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No existe un tenant asociado al contexto actual",
        )

    tenant_id = user_tenant.tenant_id
    tenant = tenant_repository.get_by_id(tenant_id=tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )

    tenant_slug = tenant.slug
    tenant_name = tenant.name
    actor = _actor_dni(current_user)
    existente = user_repository.get_by_dni(user.dni)
    es_reactivacion = False

    if existente is not None:
        nuevo_usuario = existente
        link_existente = (
            user_tenant_repository
            .get_by_user_and_tenant_including_deleted(
                existente.id,
                tenant_id,
            )
        )

        if link_existente is None:
            nuevo_user_tenant = create_tenant_link(
                user,
                nuevo_usuario,
                tenant_id,
                actor,
                user_tenant_repository,
            )
        elif link_existente.status == 3:
            es_reactivacion = True
            nuevo_user_tenant = reactivate_user(
                user,
                nuevo_usuario,
                link_existente,
                tenant_id,
                actor,
                user_repository,
                user_tenant_repository,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El usuario ya pertenece al tenant",
            )
    else:
        nuevo_usuario = create_global_user(
            user,
            tenant_id,
            actor,
            user_repository,
        )
        nuevo_user_tenant = create_tenant_link(
            user,
            nuevo_usuario,
            tenant_id,
            actor,
            user_tenant_repository,
        )

    logger.info(
        "Usuario asociado correctamente al tenant",
        extra={
            "user_id": nuevo_usuario.id,
            "dni": nuevo_usuario.dni,
            "tenant_id": tenant_id,
            "user_tenant_id": nuevo_user_tenant.id,
        },
    )

    if es_reactivacion:
        email_template = "reactivation"
        email_subject = f"Tu cuenta en {tenant_name} fue reactivada"
        email_message = (
            f"Hola {nuevo_usuario.name}, "
            f"tu cuenta en {tenant_name} ha sido reactivada exitosamente. "
            "Para completar el proceso, utiliza el botón para reactivar tu cuenta."
        )
    else:
        email_template = "activation"
        email_subject = f"Activa tu cuenta en {tenant_name}"
        email_message = (
            f"Hola {nuevo_usuario.name}, "
            f"tu cuenta en {tenant_name} ha sido creada exitosamente."
        )

    try:
        send_email(
            recipient=nuevo_user_tenant.email,
            subject=email_subject,
            message=email_message,
            dni=nuevo_usuario.dni,
            token=nuevo_user_tenant.activation_token,
            tenant_name=tenant_name,
            tenant_slug=tenant_slug,
            template=email_template,
        )
        logger.info(
            "Correo de usuario enviado",
            extra={
                "dni": nuevo_usuario.dni,
                "email": nuevo_user_tenant.email,
                "tenant_id": tenant_id,
                "template": email_template,
            },
        )
    except Exception as exc:
        logger.warning(
            "Usuario creado/reactivado pero falló el envío de correo: %s",
            exc,
        )

    try:
        if nuevo_user_tenant.phone:
            whatsapp_response = send_whatsapp(
                to_number=nuevo_user_tenant.phone,
                message=None,
                template_name="hello_world",
                parameters=None,
            )
            if whatsapp_response is not None:
                logger.info(
                    "WhatsApp de bienvenida enviado correctamente",
                    extra={
                        "dni": nuevo_usuario.dni,
                        "phone": nuevo_user_tenant.phone,
                        "tenant_id": tenant_id,
                    },
                )
    except Exception as exc:
        logger.exception(
            "Error inesperado enviando WhatsApp",
            extra={
                "dni": nuevo_usuario.dni,
                "phone": nuevo_user_tenant.phone,
                "tenant_id": tenant_id,
            },
        )

    return _user_payload(nuevo_usuario, nuevo_user_tenant)


# ============================================================
# LISTAR USUARIOS POR TENANT
# ============================================================

def list_users(
    db: Session,
    tenant_id: int,
    status_filter: int | None = None,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    users = user_repository.get_all_by_tenant(tenant_id, status_filter)
    logger.debug(
        "Usuarios consultados por tenant",
        extra={"tenant_id": tenant_id, "cantidad": len(users)},
    )
    resultado = []
    for user in users:
        link = _tenant_link(user, tenant_id, user_tenant_repository)
        resultado.append(_user_payload(user, link))
    return resultado


# ============================================================
# OBTENER USUARIO
# ============================================================

def get_user(
    dni: str,
    db: Session,
    tenant_id: int,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    usuario = _get_user_entity(dni, tenant_id, user_repository)
    link = _tenant_link(usuario, tenant_id, user_tenant_repository)
    return _user_payload(usuario, link)


# ============================================================
# ACTUALIZAR USUARIO
# ============================================================

def update_user(
    dni: str,
    datos: UserUpdate,
    db: Session,
    current_user: UserTenantDB | GlobalUserDB,
    user_tenant: UserTenantDB,
):
    return _update_user(
        dni=dni,
        datos=datos,
        db=db,
        current_user=current_user,
        user_tenant=user_tenant,
    )


# ============================================================
# ELIMINAR USUARIO
# ============================================================

def delete_user(
    dni: str,
    db: Session,
    tenant_id: int,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    usuario = _get_user_entity(dni, tenant_id, user_repository)
    link = _tenant_link(usuario, tenant_id, user_tenant_repository)
    try:
        user_tenant_repository.delete(link)
    except Exception as exc:
        logger.exception(
            "Error al eliminar usuario",
            extra={"dni": dni, "tenant_id": tenant_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al eliminar usuario",
        ) from exc
    logger.info(
        "Usuario eliminado lógicamente",
        extra={
            "dni": dni,
            "tenant_id": tenant_id,
            "user_tenant_id": link.id,
        },
    )
    return _user_payload(
        usuario,
        link,
        message="Usuario eliminado correctamente",
    )


# ============================================================
# EXPORTAR USUARIOS
# ============================================================
def export_users(
    db: Session,
    current_user: UserTenantDB | GlobalUserDB,
    tenant_id: int,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    users = user_repository.get_all_by_tenant(tenant_id, None)
    data = []
    for user in users:
        link = _tenant_link(user, tenant_id, user_tenant_repository)
        data.append(
            {
                "DNI": user.dni,
                "Nombre": user.name,
                "Email": link.email,
                "Teléfono": link.phone or "",
                "Estado": "Activo" if link.status == 1 else "Inactivo",
            }
        )
    logger.debug(
        "Usuarios exportados",
        extra={"tenant_id": tenant_id, "cantidad": len(data)},
    )
    return export_to_excel(
        data=data,
        filename="usuarios.xlsx",
        current_user=current_user,
    )


# ============================================================
# ACTIVAR USUARIO NORMAL
#
# POST /users/activate/{dni}/{token}
# ============================================================
def activate_user(
    dni: str,
    token: str,
    db: Session,
):
    tenant_id = db.execute(
        text(
            """
            SELECT users_api.resolve_tenant_id_by_activation_token(
                :activation_token
            )
            """
        ),
        {
            "activation_token": token,
        },
    ).scalar()

    if tenant_id is None:
        logger.warning(
            "Intento de activación con token inválido",
            extra={"dni": dni},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de activación inválido",
        )

    set_rls_tenant(db, tenant_id)

    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)

    usuario = user_repository.get_by_dni(dni)

    if usuario is None:
        logger.warning(
            "Intento de activación para usuario inexistente",
            extra={"dni": dni},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    link = user_tenant_repository.get_by_activation_token(token)

    if link is None:
        logger.warning(
            "Intento de activación con token inválido",
            extra={"dni": dni},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de activación inválido",
        )

    if link.user_id != usuario.id:
        logger.warning(
            "Intento de activación con token perteneciente a otro usuario",
            extra={
                "dni": dni,
                "user_id": usuario.id,
                "token_user_id": link.user_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de activación inválido",
        )

    if link.status == 3:
        logger.warning(
            "Intento de activar usuario eliminado",
            extra={"dni": dni, "user_tenant_id": link.id},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario se encuentra eliminado",
        )

    if link.status == 1:
        logger.info(
            "Intento de activar usuario que ya estaba activo",
            extra={"dni": dni, "user_tenant_id": link.id},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario ya se encuentra activo",
        )

    link.status = 1
    link.activation_token = None

    ahora = datetime.now()
    link.updated_at = ahora
    link.updated_by = "activation"
    usuario.updated_at = ahora
    usuario.updated_by = "activation"

    try:
        user_tenant_repository.update(link)
        user_repository.update(usuario)
    except IntegrityError as exc:
        logger.exception(
            "Error de integridad al activar usuario",
            extra={
                "dni": dni,
                "user_tenant_id": link.id,
                "error": str(exc),
                "orig": str(exc.orig),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fue posible activar el usuario",
        ) from exc
    except Exception as exc:
        logger.exception(
            "Error inesperado al activar usuario",
            extra={
                "dni": dni,
                "user_tenant_id": link.id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al activar usuario",
        ) from exc

    logger.info(
        "Usuario activado correctamente",
        extra={
            "dni": dni,
            "user_id": usuario.id,
            "user_tenant_id": link.id,
        },
    )

    return _user_payload(
        usuario,
        link,
        message="Usuario activado correctamente",
    )
