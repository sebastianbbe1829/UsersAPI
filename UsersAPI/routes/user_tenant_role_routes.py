from typing import List, cast

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from ..controllers import get_current_user
from ..controllers.user_tenant_role_controller import (
    asignar_rol_usuario,
    listar_roles_usuario,
    eliminar_rol_usuario,
)
from ..database import get_db
from ..models import UserDB, UserTenantDB
from ..schemas import (
    UserTenantRoleCreate,
    UserTenantRoleRead,
    UserTenantRoleDeleteResponse,
)
from ..security.dependencies import get_current_tenant


user_tenant_role_routes = APIRouter(
    prefix="/user-tenant-roles",
    tags=["Usuarios - Roles"],
)


# ============================================================
# ASIGNAR ROL A USUARIO
# ============================================================

@user_tenant_role_routes.post(
    "",
    response_model=UserTenantRoleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Asignar rol a usuario",
)
async def asignar_rol_usuario_route(
    datos: UserTenantRoleCreate,
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return asignar_rol_usuario(
        user_tenant_id=datos.user_tenant_id,
        role_id=datos.role_id,
        tenant_id = cast(int, user_tenant.tenant_id),
        db=db,
        current_user=current_user,
    )


# ============================================================
# LISTAR ROLES DE UN USUARIO
# ============================================================

@user_tenant_role_routes.get(
    "/user/{user_tenant_id}",
    response_model=List[UserTenantRoleRead],
    status_code=status.HTTP_200_OK,
    summary="Listar roles de usuario",
)
async def listar_roles_usuario_route(
    user_tenant_id: int = Path(
        ...,
        description="ID de la relación usuario-tenant",
    ),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return listar_roles_usuario(
        user_tenant_id=user_tenant_id,
        tenant_id = cast(int, user_tenant.tenant_id),
        db=db,
    )


# ============================================================
# ELIMINAR ROL DE USUARIO
# ============================================================

@user_tenant_role_routes.delete(
    "/{user_tenant_role_id}",
    response_model=UserTenantRoleDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Eliminar rol de usuario",
)
async def eliminar_rol_usuario_route(
    user_tenant_role_id: int = Path(
        ...,
        description="ID de la asignación usuario-rol",
    ),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return eliminar_rol_usuario(
        user_tenant_role_id=user_tenant_role_id,
        tenant_id = cast(int, user_tenant.tenant_id),
        db=db,
    )