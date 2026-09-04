from sqlalchemy.orm import Session

from ..models.user import UserDB
from ..schemas import RoleCreate, RoleUpdate

from ..services.role_service import (
    create_role,
    delete_role,
    get_role,
    list_roles,
    update_role,
)


def crear_rol(
    tenant_id: int,
    datos: RoleCreate,
    db: Session,
    current_user: UserDB | None = None,
):
    return create_role(
        tenant_id=tenant_id,
        code=datos.code,
        name=datos.name,
        description=datos.description,
        db=db,
        current_user=current_user,
    )


def listar_roles(
    tenant_id: int,
    db: Session,
    status_filter: int | None = None,
):
    return list_roles(
        tenant_id=tenant_id,
        db=db,
        status_filter=status_filter,
    )


def obtener_rol(
    role_id: int,
    tenant_id: int,
    db: Session,
):
    return get_role(
        role_id=role_id,
        tenant_id=tenant_id,
        db=db,
    )


def actualizar_rol(
    role_id: int,
    tenant_id: int,
    datos: RoleUpdate,
    db: Session,
    current_user: UserDB | None = None,
):
    return update_role(
        role_id=role_id,
        tenant_id=tenant_id,
        code=datos.code,
        name=datos.name,
        description=datos.description,
        status = datos.status,
        db=db,
        current_user=current_user,
    )


def eliminar_rol(
    role_id: int,
    tenant_id: int,
    db: Session,
):
    return delete_role(
        role_id=role_id,
        tenant_id=tenant_id,
        db=db,
    )