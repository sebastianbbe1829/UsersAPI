from sqlalchemy.orm import Session

from ..models import UserDB
from ..services.user_tenant_role_service import (
    assign_role_to_user,
    list_user_roles,
    delete_user_role,
)


def asignar_rol_usuario(
    user_tenant_id: int,
    role_id: int,
    tenant_id: int,
    db: Session,
    current_user: UserDB | None = None,
):
    return assign_role_to_user(
        user_tenant_id=user_tenant_id,
        role_id=role_id,
        tenant_id=tenant_id,
        db=db,
        current_user=current_user,
    )


def listar_roles_usuario(
    user_tenant_id: int,
    tenant_id: int,
    db: Session,
):
    return list_user_roles(
        user_tenant_id=user_tenant_id,
        tenant_id=tenant_id,
        db=db,
    )


def eliminar_rol_usuario(
    user_tenant_role_id: int,
    tenant_id: int,
    db: Session,
):
    return delete_user_role(
        user_tenant_role_id=user_tenant_role_id,
        tenant_id=tenant_id,
        db=db,
    )