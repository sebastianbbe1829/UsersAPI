from typing import List, cast

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from ..controllers.user_tenant_controller import listar_tenants_usuario
from ..database import get_db
from ..models import UserTenantDB
from ..schemas import UserTenantRead
from ..security.dependencies import get_current_tenant
from ..security.permissions import require_permission


user_tenant_routes = APIRouter(
    prefix="/user-tenants",
    tags=["Usuarios - Tenants"],
)


@user_tenant_routes.get(
    "/user/{user_id}",
    response_model=List[UserTenantRead],
    status_code=status.HTTP_200_OK,
    summary="Listar asociación del usuario en el tenant actual",
    dependencies=[Depends(require_permission("USER_READ"))],
)
async def listar_tenants_usuario_route(
    user_id: int = Path(..., description="ID del usuario"),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return listar_tenants_usuario(
        user_id=user_id,
        current_tenant_id=cast(int, user_tenant.tenant_id),
        db=db,
    )
