from uuid import UUID

from sqlalchemy.orm import Session

from ..schemas.client import ClientCreate, ClientUpdate
from ..services.client_service import (
    create_client,
    delete_client,
    get_client,
    list_clients,
    update_client,
)


def crear_cliente(
    data: ClientCreate,
    db: Session,
    tenant_id: int,
    current_user: object,
):
    return create_client(data, db, tenant_id, current_user)


def listar_clientes(db: Session, tenant_id: int):
    return list_clients(db, tenant_id)


def obtener_cliente(client_id: UUID, db: Session, tenant_id: int):
    return get_client(client_id, db, tenant_id)


def actualizar_cliente(
    client_id: UUID,
    data: ClientUpdate,
    db: Session,
    tenant_id: int,
    current_user: object,
):
    return update_client(client_id, data, db, tenant_id, current_user)


def eliminar_cliente(client_id: UUID, db: Session, tenant_id: int):
    return delete_client(client_id, db, tenant_id)
