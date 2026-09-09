from uuid import UUID

from sqlalchemy.orm import Session

from UsersAPI.domains.core.models import UserTenantDB

from ..schemas import SaleCreate, SaleDraftCreate
from ..services import (
    create_draft,
    create_sale,
    delete_draft,
    get_draft,
    get_sale,
    list_drafts,
    list_sales,
)


def create(
    data: SaleCreate,
    db: Session,
    tenant_id: int,
    current_user: UserTenantDB,
    is_autoconsumption: bool = False,
):
    return create_sale(
        data,
        db,
        tenant_id,
        current_user,
        is_autoconsumption=is_autoconsumption,
    )


def create_frozen(
    data: SaleDraftCreate,
    db: Session,
    tenant_id: int,
    current_user: UserTenantDB,
    is_autoconsumption: bool = False,
):
    return create_draft(
        data,
        db,
        tenant_id,
        current_user,
        is_autoconsumption=is_autoconsumption,
    )


def get_frozen(draft_id: UUID, db: Session, tenant_id: int):
    return get_draft(draft_id, db, tenant_id)


def list_frozen(db: Session, tenant_id: int):
    return list_drafts(db, tenant_id)


def delete_frozen(draft_id: UUID, db: Session, tenant_id: int):
    return delete_draft(draft_id, db, tenant_id)


def get(sale_id: UUID, db: Session, tenant_id: int):
    return get_sale(sale_id, db, tenant_id)


def list_all(db: Session, tenant_id: int, limit: int = 100, offset: int = 0):
    return list_sales(db, tenant_id, limit=limit, offset=offset)
