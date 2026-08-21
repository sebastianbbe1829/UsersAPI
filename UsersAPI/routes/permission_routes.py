from typing import List

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from ..controllers.permission_controller import obtener_permiso, listar_permisos
from ..database import get_db
from ..schemas import PermissionResponse
from ..security.permissions import require_permission
from ..models import UserDB

from ..controllers import (
    listar_tenants,
    get_current_user,
)

permission_routes = APIRouter(
    prefix="/permission",
    tags=["Permission"],
)


@permission_routes.get(
    "",
    response_model=List[PermissionResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar permissions",
    dependencies=[
        Depends(require_permission("PERMISSION_READ")),
    ],
)
async def listar_permission_route(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    return listar_permisos(
        db,
    )


@permission_routes.get(
    "/{permission_code}",
    response_model=PermissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener permiso por código",
    dependencies=[
        Depends(require_permission("PERMISSION_READ")),
    ],
)
async def obtener_permission_route(
    permission_code: str = Path(
        ...,
        description="Código del permiso",
    ),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return obtener_permiso(
        permission_code,
        db,
    )
