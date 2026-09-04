from uuid import UUID

from sqlalchemy.orm import Session

from ..models import GlobalUserDB, UserTenantDB
from ..schemas import ClientCreate, ClientUpdate
from ..services.client_service import (
    create_client,
    delete_client,
    get_client,
    list_clients,
    search_clients,
    update_client,
)


def crear_cliente(
    data: ClientCreate,
    db: Session,
    current_user: UserTenantDB | GlobalUserDB,
    tenant_id: int,
):
    return create_client(data, db, current_user, tenant_id)


def listar_clientes(db: Session, tenant_id: int, include_inactive: bool = False):
    return list_clients(db, tenant_id, include_inactive)


def buscar_clientes(db: Session, tenant_id: int, search: str = "", limit: int = 20):
    return search_clients(db, tenant_id, search, limit)


def obtener_cliente(client_uuid: UUID, db: Session, tenant_id: int):
    return get_client(client_uuid, db, tenant_id)


def actualizar_cliente(
    client_uuid: UUID,
    data: ClientUpdate,
    db: Session,
    current_user: UserTenantDB | GlobalUserDB,
    tenant_id: int,
):
    return update_client(client_uuid, data, db, current_user, tenant_id)


def eliminar_cliente(
    client_uuid: UUID,
    db: Session,
    current_user: UserTenantDB | GlobalUserDB,
    tenant_id: int,
):
    return delete_client(client_uuid, db, current_user, tenant_id)
