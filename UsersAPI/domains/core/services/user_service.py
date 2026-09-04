from sqlalchemy.orm import Session

from ..models import GlobalUserDB, UserTenantDB
from ..schemas import UserCreate, UserUpdate
from .user_creation_service import create_user as _create_user
from .user_update_service import update_user as _update_user
from .user_delete_service import delete_user as _delete_user
from .user_export_service import export_users as _export_users
from .user_activation_service import activate_user as _activate_user
from .user_read_service import list_users as _list_users, get_user as _get_user


def create_user(
    user: UserCreate,
    db: Session,
    current_user: UserTenantDB | GlobalUserDB | None = None,
    user_tenant: UserTenantDB | None = None,
):
    return _create_user(
        user=user,
        db=db,
        current_user=current_user,
        user_tenant=user_tenant,
    )


def list_users(
    db: Session,
    tenant_id: int,
    status_filter: int | None = None,
):
    return _list_users(
        db=db,
        tenant_id=tenant_id,
        status_filter=status_filter,
    )


def get_user(
    dni: str,
    db: Session,
    tenant_id: int,
):
    return _get_user(
        dni=dni,
        db=db,
        tenant_id=tenant_id,
    )


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
