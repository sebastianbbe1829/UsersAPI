from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from UsersAPI.domains.core.models import GlobalUserDB, UserTenantDB

from ..repositories.client_repository import ClientRepository
from ..schemas.client import ClientCreate, ClientUpdate
from ..schemas.compliance_override import ClientComplianceOverrideRequest
from ..services.client_service import (
    create_client,
    delete_client,
    get_client,
    list_clients,
    update_client,
)
from ..services.compliance_override_service import override_client_compliance
from ..services.compliance_report_service import (
    list_compliance_override_history,
    list_restricted_clients_report,
)
from ..services.screening_service import screen_client


def crear_cliente(data: ClientCreate, db: Session, tenant_id: int, current_user: object):
    return create_client(data, db, tenant_id, current_user)


def listar_clientes(
    db: Session,
    tenant_id: int,
    limit: int | None = None,
    offset: int = 0,
    search: str | None = None,
):
    return list_clients(
        db,
        tenant_id,
        limit=limit,
        offset=offset,
        search=search,
    )


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


def levantar_restriccion_cliente(
    client_id: UUID,
    data: ClientComplianceOverrideRequest,
    db: Session,
    tenant_id: int,
    current_user: UserTenantDB | GlobalUserDB,
):
    return override_client_compliance(client_id, data, db, tenant_id, current_user)


def revisar_cliente_listas(client_id: UUID, db: Session, tenant_id: int):
    client = ClientRepository(db).get_by_id(client_id, tenant_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return screen_client(client, db)


def informe_listas_restrictivas(db: Session, tenant_id: int):
    return list_restricted_clients_report(db, tenant_id)


def historial_levantamientos_restriccion(db: Session, tenant_id: int):
    return list_compliance_override_history(db, tenant_id)
