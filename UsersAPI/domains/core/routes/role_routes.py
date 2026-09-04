from typing import List, cast

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from ..controllers import (
    crear_rol,
    listar_roles,
    obtener_rol,
    actualizar_rol,
    eliminar_rol,
    get_current_user,
)
from ..database import get_db
from ..models import UserDB, UserTenantDB
from ..schemas import (
    RoleCreate,
    RoleDeleteResponse,
    RoleRead,
    RoleUpdate,
)
from ..security.dependencies import get_current_tenant
from ..security.permissions import require_permission


role_routes = APIRouter(
    prefix="/roles",
    tags=["Roles"],
)


# ============================================================
# CREAR ROL
# POST /roles
# Permiso requerido: ROLE_CREATE
# ============================================================

@role_routes.post(
    "",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear rol",
    dependencies=[
        Depends(require_permission("ROLE_CREATE")),
    ],
)
async def crear_rol_route(
    datos: RoleCreate,
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return crear_rol(
        tenant_id=cast(int, user_tenant.tenant_id),
        datos=datos,
        db=db,
        current_user=current_user,
    )


# ============================================================
# LISTAR ROLES
# GET /roles
# Permiso requerido: ROLE_READ
# ============================================================

@role_routes.get(
    "",
    response_model=List[RoleRead],
    status_code=status.HTTP_200_OK,
    summary="Listar roles del tenant",
    dependencies=[
        Depends(require_permission("ROLE_READ")),
    ],
)
async def listar_roles_route(
    status_filter: int | None = Query(
        None,
        description="Filtra roles por estado (0=inactivo, 1=activo)",
    ),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return listar_roles(
        tenant_id=cast(int, user_tenant.tenant_id),
        db=db,
        status_filter=status_filter,
    )


# ============================================================
# OBTENER ROL
# GET /roles/{role_id}
# Permiso requerido: ROLE_READ
# ============================================================

@role_routes.get(
    "/{role_id}",
    response_model=RoleRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener rol",
    dependencies=[
        Depends(require_permission("ROLE_READ")),
    ],
)
async def obtener_rol_route(
    role_id: int = Path(
        ...,
        description="ID del rol",
    ),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return obtener_rol(
        role_id=role_id,
        tenant_id=cast(int, user_tenant.tenant_id),
        db=db,
    )


# ============================================================
# ACTUALIZAR ROL
# PATCH /roles/{role_id}
# Permiso requerido: ROLE_UPDATE
# ============================================================

@role_routes.patch(
    "/{role_id}",
    response_model=RoleRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar rol",
    dependencies=[
        Depends(require_permission("ROLE_UPDATE")),
    ],
)
async def actualizar_rol_route(
    role_id: int,
    datos: RoleUpdate,
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return actualizar_rol(
        role_id=role_id,
        tenant_id=cast(int, user_tenant.tenant_id),
        datos=datos,
        db=db,
        current_user=current_user,
    )


# ============================================================
# ELIMINAR ROL
# DELETE /roles/{role_id}
# Permiso requerido: ROLE_DELETE
# ============================================================

@role_routes.delete(
    "/{role_id}",
    response_model=RoleDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Eliminar rol",
    dependencies=[
        Depends(require_permission("ROLE_DELETE")),
    ],
)
async def eliminar_rol_route(
    role_id: int = Path(
        ...,
        description="ID del rol",
    ),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return eliminar_rol(
        role_id=role_id,
        tenant_id=cast(int, user_tenant.tenant_id),
        db=db,
    )