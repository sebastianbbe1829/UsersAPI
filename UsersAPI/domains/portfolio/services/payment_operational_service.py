from uuid import UUID

from sqlalchemy.orm import Session

from UsersAPI.domains.clients.services.client_service import list_clients

from .portfolio_service import list_client_obligations


def search_payment_clients(
    db: Session,
    tenant_id: int,
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    return list_clients(db, tenant_id, limit=limit, offset=offset, search=search)


def get_payment_client_obligations(client_id: UUID, db: Session, tenant_id: int):
    return list_client_obligations(client_id, db, tenant_id)
