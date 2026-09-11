from uuid import UUID

from sqlalchemy.orm import Session

from UsersAPI.domains.clients.services.client_service import list_clients
from UsersAPI.domains.inventory.services import (
    list_inventory,
    list_products,
    list_top_selling_products,
)
from UsersAPI.domains.portfolio.services import get_client_credit


def get_pos_catalog(db: Session, tenant_id: int):
    return {
        "products": list_products(db, tenant_id, active_only=True),
        "top_products": list_top_selling_products(db, tenant_id, limit=6),
        "inventory": list_inventory(db, tenant_id),
    }


def search_pos_clients(
    db: Session,
    tenant_id: int,
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    return list_clients(db, tenant_id, limit=limit, offset=offset, search=search)


def get_pos_client_credit(client_id: UUID, db: Session, tenant_id: int):
    return get_client_credit(client_id, db, tenant_id)
