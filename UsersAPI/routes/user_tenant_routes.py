from typing import List, cast

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
from ..models import UserDB, UserTenantDB
from ..schemas import (
    UserTenantCreate,
    UserTenantDeleteResponse,
    UserTenantRead,
)
from ..security.dependencies import get_current_tenant
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
# La asociación solo puede crearse dentro del tenant actual.
# El tenant_id enviado por el cliente debe coincidir con el
# tenant obtenido del contexto autenticado.
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
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    return crear_user_tenant(
        datos=datos,
        current_tenant_id=cast(int, user_tenant.tenant_id),
        db=db,
        current_user=current_user,
    )


# ============================================================
# OBTENER ASOCIACIÓN USUARIO-TENANT
#
# GET /user-tenants/{user_tenant_id}
#
# Solo permite acceder a asociaciones del tenant actual.
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
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):

    return obtener_user_tenant(
        user_tenant_id=user_tenant_id,
        current_tenant_id=cast(int, user_tenant.tenant_id),
        db=db,
    )


# ============================================================
# LISTAR TENANTS DE UN USUARIO
#
# GET /user-tenants/user/{user_id}
#
# Devuelve únicamente la asociación del usuario dentro del
# tenant actual. La pertenencia global se consulta mediante
# GET /tenants/my.
#
# Permiso requerido:
#   USER_READ
# ============================================================

@user_tenant_routes.get(
    "/user/{user_id}",
    response_model=List[UserTenantRead],
    status_code=status.HTTP_200_OK,
    summary="Listar asociación del usuario en el tenant actual",
    dependencies=[
        Depends(require_permission("USER_READ")),
    ],
)
async def listar_tenants_usuario_route(
    user_id: int = Path(
        ...,
        description="ID del usuario",
    ),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):

    return listar_tenants_usuario(
        user_id=user_id,
        current_tenant_id=cast(int, user_tenant.tenant_id),
        db=db,
    )


# ============================================================
# LISTAR USUARIOS DE UN TENANT
#
# GET /user-tenants/tenant/{tenant_id}
#
# Solo permite listar usuarios del tenant actual.
#
# Permiso requerido:
#   USER_READ
# ============================================================

@user_tenant_routes.get(
    "/tenant/{tenant_id}",
    response_model=List[UserTenantRead],
    status_code=status.HTTP_200_OK,
    summary="Listar usuarios del tenant actual",
    dependencies=[
        Depends(require_permission("USER_READ")),
    ],
)
async def listar_usuarios_tenant_route(
    tenant_id: int = Path(
        ...,
        description="ID del tenant",
    ),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):

    return listar_usuarios_tenant(
        tenant_id=tenant_id,
        current_tenant_id=cast(int, user_tenant.tenant_id),
        db=db,
    )


# ============================================================
# ELIMINAR ASOCIACIÓN USUARIO-TENANT
#
# DELETE /user-tenants/{user_tenant_id}
#
# Solo permite eliminar asociaciones del tenant actual.
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
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):

    return eliminar_user_tenant(
        user_tenant_id=user_tenant_id,
        current_tenant_id=cast(int, user_tenant.tenant_id),
        db=db,
    )
