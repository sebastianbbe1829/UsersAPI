from sqlalchemy.orm import Session

from ..models.user import UserDB
from ..schemas import UserTenantCreate
from ..services.user_tenant_service import (
    delete_user_tenant,
    get_user_tenant,
    list_tenant_users,
    list_user_tenants,
)


# ============================================================
# LISTAR TENANT DE UN USUARIO DENTRO DEL CONTEXTO ACTUAL
# ============================================================

def listar_tenants_usuario(
    user_id: int,
    current_tenant_id: int,
    db: Session,
):

    return list_user_tenants(
        user_id=user_id,
        current_tenant_id=current_tenant_id,
        db=db,
    )


# ============================================================
# LISTAR USUARIOS DEL TENANT ACTUAL
# ============================================================

def listar_usuarios_tenant(
    tenant_id: int,
    current_tenant_id: int,
    db: Session,
):

    return list_tenant_users(
        tenant_id=tenant_id,
        current_tenant_id=current_tenant_id,
        db=db,
    )


# ============================================================
# OBTENER ASOCIACIÓN
# ============================================================

def obtener_user_tenant(
    user_tenant_id: int,
    current_tenant_id: int,
    db: Session,
):

    return get_user_tenant(
        user_tenant_id=user_tenant_id,
        current_tenant_id=current_tenant_id,
        db=db,
    )


# ============================================================
# ELIMINAR ASOCIACIÓN
# ============================================================

def eliminar_user_tenant(
    user_tenant_id: int,
    current_tenant_id: int,
    db: Session,
):

    return delete_user_tenant(
        user_tenant_id=user_tenant_id,
        current_tenant_id=current_tenant_id,
        db=db,
    )
