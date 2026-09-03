import uuid
from datetime import datetime

from fastapi import HTTPException, status
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
# OBTENER ASOCIACIÓN
# ============================================================

def get_user_tenant(
    user_tenant_id: int,
    current_tenant_id: int,
    db: Session,
) -> UserTenantDB:

    repository = UserTenantRepository(db)

    asociacion = repository.get_by_id(user_tenant_id)

    if asociacion is None or asociacion.tenant_id != current_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asociación usuario-tenant no encontrada",
        )

    return asociacion


# ============================================================
# LISTAR TENANTS DE UN USUARIO DENTRO DEL CONTEXTO ACTUAL
# ============================================================

def list_user_tenants(
    user_id: int,
    current_tenant_id: int,
    db: Session,
):

    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)

    usuario = user_repository.get_by_id_including_deleted(user_id)

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no existe",
        )

    asociacion = user_tenant_repository.get_by_user_and_tenant(
        user_id=user_id,
        tenant_id=current_tenant_id,
    )

    if asociacion is None:
        return []

    return [asociacion]


# ============================================================
# LISTAR USUARIOS DE UN TENANT
# ============================================================

def list_tenant_users(
    tenant_id: int,
    current_tenant_id: int,
    db: Session,
):

    if tenant_id != current_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )

    tenant_repository = TenantRepository(db)
    user_tenant_repository = UserTenantRepository(db)

    tenant = tenant_repository.get_by_id(current_tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El tenant no existe",
        )

    return user_tenant_repository.get_by_tenant(current_tenant_id)


# ============================================================
# ELIMINAR ASOCIACIÓN USUARIO - TENANT
# ============================================================

def delete_user_tenant(
    user_tenant_id: int,
    current_tenant_id: int,
    db: Session,
):

    repository = UserTenantRepository(db)

    asociacion = repository.get_by_id(user_tenant_id)

    if asociacion is None or asociacion.tenant_id != current_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asociación usuario-tenant no encontrada",
        )

    asociacion.status = 3
    asociacion.updated_at = datetime.now()

    repository.mark_dirty(asociacion)

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
        "message": "Asociación usuario-tenant eliminada correctamente",
    }
