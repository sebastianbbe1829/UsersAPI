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
from ..security.permissions import require_permission


user_tenant_routes = APIRouter(
    prefix="/user-tenants",
    tags=["Usuarios - Tenants"],
)


# ============================================================
# ASOCIAR USUARIO A TENANT
#
# POST /user-tenants
#
# Permiso requerido:
#   USER_UPDATE
# ============================================================

@user_tenant_routes.post(
    "",
    response_model=UserTenantRead,
    status_code=status.HTTP_201_CREATED,
    summary="Asociar usuario a tenant",
    dependencies=[
        Depends(require_permission("USER_UPDATE")),
    ],
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


# ============================================================
# OBTENER ASOCIACIÓN USUARIO-TENANT
#
# GET /user-tenants/{user_tenant_id}
#
# Permiso requerido:
#   USER_READ
# ============================================================

@user_tenant_routes.get(
    "/{user_tenant_id}",
    response_model=UserTenantRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener asociación usuario-tenant",
    dependencies=[
        Depends(require_permission("USER_READ")),
    ],
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


# ============================================================
# LISTAR TENANTS DE UN USUARIO
#
# GET /user-tenants/user/{user_id}
#
# Permiso requerido:
#   USER_READ
# ============================================================

@user_tenant_routes.get(
    "/user/{user_id}",
    response_model=List[UserTenantRead],
    status_code=status.HTTP_200_OK,
    summary="Listar tenants de un usuario",
    dependencies=[
        Depends(require_permission("USER_READ")),
    ],
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


# ============================================================
# LISTAR USUARIOS DE UN TENANT
#
# GET /user-tenants/tenant/{tenant_id}
#
# Permiso requerido:
#   USER_READ
# ============================================================

@user_tenant_routes.get(
    "/tenant/{tenant_id}",
    response_model=List[UserTenantRead],
    status_code=status.HTTP_200_OK,
    summary="Listar usuarios de un tenant",
    dependencies=[
        Depends(require_permission("USER_READ")),
    ],
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


# ============================================================
# ELIMINAR ASOCIACIÓN USUARIO-TENANT
#
# DELETE /user-tenants/{user_tenant_id}
#
# Permiso requerido:
#   USER_UPDATE
# ============================================================

@user_tenant_routes.delete(
    "/{user_tenant_id}",
    response_model=UserTenantDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Eliminar asociación usuario-tenant",
    dependencies=[
        Depends(require_permission("USER_UPDATE")),
    ],
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