from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from UsersAPI.domains.core.controllers import get_current_user
from UsersAPI.domains.core.database import get_db
from UsersAPI.domains.core.models import UserTenantDB
from UsersAPI.security.dependencies import get_current_tenant
from UsersAPI.security.permissions import require_permission

from ..controllers.client_controller import (
    actualizar_cliente,
    crear_cliente,
    eliminar_cliente,
    listar_clientes,
    obtener_cliente,
)
from ..schemas.client import ClientCreate, ClientRead, ClientUpdate


client_routes = APIRouter(
    prefix="/clients",
    tags=["Clientes"],
)


@client_routes.post(
    "",
    response_model=ClientRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("CLIENT_CREATE"))],
)
async def create_client_route(
    data: ClientCreate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return crear_cliente(data, db, cast(int, user_tenant.tenant_id), current_user)


@client_routes.get(
    "",
    response_model=list[ClientRead],
    dependencies=[Depends(require_permission("CLIENT_READ"))],
)
async def list_clients_route(
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return listar_clientes(db, cast(int, user_tenant.tenant_id))


@client_routes.get(
    "/{client_id}",
    response_model=ClientRead,
    dependencies=[Depends(require_permission("CLIENT_READ"))],
)
async def get_client_route(
    client_id: UUID,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return obtener_cliente(client_id, db, cast(int, user_tenant.tenant_id))


@client_routes.patch(
    "/{client_id}",
    response_model=ClientRead,
    dependencies=[Depends(require_permission("CLIENT_UPDATE"))],
)
async def update_client_route(
    client_id: UUID,
    data: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return actualizar_cliente(
        client_id,
        data,
        db,
        cast(int, user_tenant.tenant_id),
        current_user,
    )


@client_routes.delete(
    "/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("CLIENT_DELETE"))],
)
async def delete_client_route(
    client_id: UUID,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    eliminar_cliente(client_id, db, cast(int, user_tenant.tenant_id))
