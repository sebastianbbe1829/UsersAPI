from sqlalchemy.orm import Session

from ..models import UserDB
from ..services.role_permission_service import (
    assign_permission_to_role,
    list_role_permissions,
    remove_permission_from_role,
)


# ============================================================
# ASIGNAR PERMISO A ROL
# ============================================================

def asignar_permiso_rol(
    role_id: int,
    permission_id: int,
    tenant_id: int,
    db: Session,
    current_user: UserDB,
):

    return assign_permission_to_role(
        role_id=role_id,
        permission_id=permission_id,
        tenant_id=tenant_id,
        db=db,
        current_user=current_user,
    )


# ============================================================
# LISTAR PERMISOS DE UN ROL
# ============================================================

def listar_permisos_rol(
    role_id: int,
    tenant_id: int,
    db: Session,
):

    return list_role_permissions(
        role_id=role_id,
        tenant_id=tenant_id,
        db=db,
    )


# ============================================================
# ELIMINAR PERMISO DE ROL
# ============================================================

def eliminar_permiso_rol(
    role_permission_id: int,
    tenant_id: int,
    db: Session,
):

    return remove_permission_from_role(
        role_permission_id=role_permission_id,
        tenant_id=tenant_id,
        db=db,
    )