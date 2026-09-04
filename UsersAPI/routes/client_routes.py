from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from ..controllers import client_controller, get_current_user
from ..database import get_db
from ..models import GlobalUserDB, UserTenantDB
from ..schemas import ClientCreate, ClientDeleteResponse, ClientRead, ClientUpdate
from ..security.dependencies import get_current_tenant
from ..security.permissions import require_permission


client_routes = APIRouter(prefix="/clients", tags=["Clientes"])


@client_routes.post(
    "",
    response_model=ClientRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear cliente",
    dependencies=[Depends(require_permission("CLIENT_CREATE"))],
)
async def crear_cliente(
    data: ClientCreate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB | GlobalUserDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return client_controller.crear_cliente(
        data,
        db,
        current_user,
        cast(int, user_tenant.tenant_id),
    )


@client_routes.get(
    "/search",
    response_model=list[ClientRead],
    summary="Buscar clientes",
    dependencies=[Depends(require_permission("CLIENT_READ"))],
)
async def buscar_clientes(
    search: str = Query("", max_length=100),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return client_controller.buscar_clientes(
        db,
        cast(int, user_tenant.tenant_id),
        search,
        limit,
    )


@client_routes.get(
    "",
    response_model=list[ClientRead],
    summary="Listar clientes",
    dependencies=[Depends(require_permission("CLIENT_READ"))],
)
async def listar_clientes(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return client_controller.listar_clientes(
        db,
        cast(int, user_tenant.tenant_id),
        include_inactive,
    )


@client_routes.get(
    "/{client_uuid}",
    response_model=ClientRead,
    summary="Obtener cliente",
    dependencies=[Depends(require_permission("CLIENT_READ"))],
)
async def obtener_cliente(
    client_uuid: UUID = Path(...),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return client_controller.obtener_cliente(
        client_uuid,
        db,
        cast(int, user_tenant.tenant_id),
    )


@client_routes.patch(
    "/{client_uuid}",
    response_model=ClientRead,
    summary="Actualizar cliente",
    dependencies=[Depends(require_permission("CLIENT_UPDATE"))],
)
async def actualizar_cliente(
    data: ClientUpdate,
    client_uuid: UUID = Path(...),
    db: Session = Depends(get_db),
    current_user: UserTenantDB | GlobalUserDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return client_controller.actualizar_cliente(
        client_uuid,
        data,
        db,
        current_user,
        cast(int, user_tenant.tenant_id),
    )


@client_routes.delete(
    "/{client_uuid}",
    response_model=ClientDeleteResponse,
    summary="Desactivar cliente",
    dependencies=[Depends(require_permission("CLIENT_DELETE"))],
)
async def eliminar_cliente(
    client_uuid: UUID = Path(...),
    db: Session = Depends(get_db),
    current_user: UserTenantDB | GlobalUserDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return client_controller.eliminar_cliente(
        client_uuid,
        db,
        current_user,
        cast(int, user_tenant.tenant_id),
    )
