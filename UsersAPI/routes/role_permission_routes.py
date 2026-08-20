from typing import List, cast

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from ..controllers import get_current_user
from ..controllers.role_permission_controller import (
    asignar_permiso_rol,
    listar_permisos_rol,
    eliminar_permiso_rol,
)
from ..database import get_db
from ..models import UserDB, UserTenantDB
from ..schemas import (
    RolePermissionCreate,
    RolePermissionRead,
    RolePermissionDeleteResponse,
)
from ..security.dependencies import get_current_tenant


role_permission_routes = APIRouter(
    prefix="/role-permissions",
    tags=["Roles - Permisos"],
)


# ============================================================
# ASIGNAR PERMISO A ROL
# ============================================================

@role_permission_routes.post(
    "",
    response_model=RolePermissionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Asignar permiso a rol",
)
async def asignar_permiso_rol_route(
    datos: RolePermissionCreate,
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    return asignar_permiso_rol(
        role_id=datos.role_id,
        permission_id=datos.permission_id,
        tenant_id=cast(int, user_tenant.tenant_id),
        db=db,
        current_user=current_user,
    )


# ============================================================
# LISTAR PERMISOS DE UN ROL
# ============================================================

@role_permission_routes.get(
    "/role/{role_id}",
    response_model=List[RolePermissionRead],
    status_code=status.HTTP_200_OK,
    summary="Listar permisos de un rol",
)
async def listar_permisos_rol_route(
    role_id: int = Path(
        ...,
        description="ID del rol",
    ),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    return listar_permisos_rol(
        role_id=role_id,
        tenant_id=cast(int, user_tenant.tenant_id),
        db=db,
    )


# ============================================================
# ELIMINAR PERMISO DE UN ROL
# ============================================================

@role_permission_routes.delete(
    "/{role_permission_id}",
    response_model=RolePermissionDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Eliminar permiso de rol",
)
async def eliminar_permiso_rol_route(
    role_permission_id: int = Path(
        ...,
        description="ID de la relación rol-permiso",
    ),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    return eliminar_permiso_rol(
        role_permission_id=role_permission_id,
        tenant_id=cast(int, user_tenant.tenant_id),
        db=db,
    )