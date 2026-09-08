from uuid import UUID

from sqlalchemy.orm import Session

from UsersAPI.domains.core.models import UserTenantDB

from ..schemas import SaleCreate
from ..services import create_sale, get_sale, list_sales


def create(data: SaleCreate, db: Session, tenant_id: int, current_user: UserTenantDB):
    return create_sale(data, db, tenant_id, current_user)


def get(sale_id: UUID, db: Session, tenant_id: int):
    return get_sale(sale_id, db, tenant_id)


def list_all(db: Session, tenant_id: int, limit: int = 100, offset: int = 0):
    return list_sales(db, tenant_id, limit=limit, offset=offset)
