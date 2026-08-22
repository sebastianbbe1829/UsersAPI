from sqlalchemy.orm import Session

from ..models.user import UserDB
from ..schemas import TenantCreate, TenantUpdate
from ..services.tenant_service import (
    create_tenant,
    delete_tenant,
    get_tenant,
    list_my_tenants,
    list_tenants,
    update_tenant,
)


def crear_tenant(
    tenant: TenantCreate,
    db: Session,
    current_user: UserDB | None = None,
):
    return create_tenant(
        name=tenant.name,
        slug=tenant.slug,
        db=db,
        current_user=current_user,
    )


def listar_tenants(
    tenant_id: int,
    db: Session,
    status: int | None = None,
):
    return list_tenants(
        tenant_id=tenant_id,
        db=db,
        status_filter=status,
    )


def listar_mis_tenants(
    db: Session,
    current_user: UserDB,
):
    return list_my_tenants(
        db=db,
        current_user=current_user,
    )


def obtener_tenant(
    tenant_id: int,
    current_tenant_id: int,
    db: Session,
):
    return get_tenant(
        tenant_id=tenant_id,
        current_tenant_id=current_tenant_id,
        db=db,
    )


def actualizar_tenant(
    tenant_id: int,
    current_tenant_id: int,
    datos: TenantUpdate,
    db: Session,
    current_user: UserDB | None = None,
):
    return update_tenant(
        tenant_id=tenant_id,
        current_tenant_id=current_tenant_id,
        name=datos.name,
        slug=datos.slug,
        db=db,
        current_user=current_user,
    )


def eliminar_tenant(
    tenant_id: int,
    current_tenant_id: int,
    db: Session,
):
    return delete_tenant(
        tenant_id=tenant_id,
        current_tenant_id=current_tenant_id,
        db=db,
    )
