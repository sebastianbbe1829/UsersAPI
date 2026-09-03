from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import GlobalUserDB, UserDB, UserTenantDB
from ..repositories.user_repository import UserRepository
from ..repositories.user_tenant_repository import UserTenantRepository
from ..schemas import UserCreate, UserUpdate
from ..repositories.tenant_repository import TenantRepository
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
from .user_delete_service import delete_user as _delete_user
from .user_export_service import export_users as _export_users
from .user_activation_service import activate_user as _activate_user
from .user_notification_service import send_user_notifications


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

    send_user_notifications(
        user=nuevo_usuario,
        user_tenant=nuevo_user_tenant,
        tenant_name=tenant_name,
        tenant_slug=tenant_slug,
        es_reactivacion=es_reactivacion,
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
    return _delete_user(
        dni=dni,
        db=db,
        tenant_id=tenant_id,
    )


# ============================================================
# EXPORTAR USUARIOS
# ============================================================
def export_users(
    db: Session,
    current_user: UserTenantDB | GlobalUserDB,
    tenant_id: int,
):
    return _export_users(
        db=db,
        current_user=current_user,
        tenant_id=tenant_id,
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
    return _activate_user(
        dni=dni,
        token=token,
        db=db,
    )
