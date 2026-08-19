from typing import List

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from ..controllers import get_current_user
from ..controllers.user_tenant_controller import (
    crear_user_tenant,
    eliminar_user_tenant,
    listar_tenants_usuario,
    listar_usuarios_tenant,
    obtener_user_tenant,
)
from ..database import get_db
from ..models import UserDB
from ..schemas import (
    UserTenantCreate,
    UserTenantDeleteResponse,
    UserTenantRead,
)


user_tenant_routes = APIRouter(
    prefix="/user-tenants",
    tags=["Usuarios - Tenants"],
)


@user_tenant_routes.post(
    "",
    response_model=UserTenantRead,
    status_code=status.HTTP_201_CREATED,
    summary="Asociar usuario a tenant",
)
async def crear_user_tenant_route(
    datos: UserTenantCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return crear_user_tenant(
        datos,
        db,
        current_user,
    )


@user_tenant_routes.get(
    "/{user_tenant_id}",
    response_model=UserTenantRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener asociación usuario-tenant",
)
async def obtener_user_tenant_route(
    user_tenant_id: int = Path(
        ...,
        description="ID de la asociación usuario-tenant",
    ),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return obtener_user_tenant(
        user_tenant_id,
        db,
    )


@user_tenant_routes.get(
    "/user/{user_id}",
    response_model=List[UserTenantRead],
    status_code=status.HTTP_200_OK,
    summary="Listar tenants de un usuario",
)
async def listar_tenants_usuario_route(
    user_id: int = Path(
        ...,
        description="ID del usuario",
    ),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return listar_tenants_usuario(
        user_id,
        db,
    )


@user_tenant_routes.get(
    "/tenant/{tenant_id}",
    response_model=List[UserTenantRead],
    status_code=status.HTTP_200_OK,
    summary="Listar usuarios de un tenant",
)
async def listar_usuarios_tenant_route(
    tenant_id: int = Path(
        ...,
        description="ID del tenant",
    ),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return listar_usuarios_tenant(
        tenant_id,
        db,
    )


@user_tenant_routes.delete(
    "/{user_tenant_id}",
    response_model=UserTenantDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Eliminar asociación usuario-tenant",
)
async def eliminar_user_tenant_route(
    user_tenant_id: int = Path(
        ...,
        description="ID de la asociación usuario-tenant",
    ),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return eliminar_user_tenant(
        user_tenant_id,
        db,
    )