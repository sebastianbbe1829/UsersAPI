from sqlalchemy.orm import Session

from ..schemas import UserCreate, UserUpdate
from ..models import UserTenantDB

from ..services.user_service import (
    create_user,
    export_users,
    get_user,
    list_users,
    update_user,
    delete_user,
)


# ============================================================
# CREAR USUARIO
# ============================================================

def crear_usuario(
    user: UserCreate,
    db: Session,
    current_user: UserTenantDB | None = None,
    user_tenant: UserTenantDB | None = None,
):
    return create_user(
        user,
        db,
        current_user,
        user_tenant,
    )


# ============================================================
# LISTAR USUARIOS POR TENANT
# ============================================================

def listar_usuarios(
    db: Session,
    tenant_id: int,
    status_filter: int | None = None,
):
    return list_users(
        db=db,
        tenant_id=tenant_id,
        status_filter=status_filter,
    )


# ============================================================
# CONSULTAR USUARIO
# ============================================================

def obtener_usuario(
    dni: str,
    db: Session,
    user_tenant: UserTenantDB,
):
    return get_user(
        dni=dni,
        tenant_id=user_tenant.tenant_id,
        db=db,
    )


# ============================================================
# ACTUALIZAR USUARIO
# ============================================================

def actualizar_usuario(
    dni: str,
    datos: UserUpdate,
    db: Session,
    current_user: UserTenantDB,
    user_tenant: UserTenantDB,
):
    return update_user(
        dni,
        datos,
        db,
        current_user,
        user_tenant,
    )


# ============================================================
# ELIMINAR USUARIO
# ============================================================

def eliminar_usuario(
    dni: str,
    db: Session,
    user_tenant: UserTenantDB,
):
    return delete_user(
        dni,
        db,
        user_tenant.tenant_id,
    )


# ============================================================
# EXPORTAR USUARIOS
# ============================================================

def exportar_usuarios(
    db: Session,
    current_user: UserTenantDB,
    user_tenant: UserTenantDB,
):
    return export_users(
        db,
        current_user,
        user_tenant.tenant_id,
    )