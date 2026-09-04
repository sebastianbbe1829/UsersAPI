from typing import List

from fastapi import (
    APIRouter,
    Depends,
    Path,
    status,
)
from sqlalchemy.orm import Session

from ..controllers.permission_controller import (
    obtener_permiso,
    listar_permisos,
    crear_permiso,
)

from ..database import get_db

from ..schemas import (
    PermissionCreate,
    PermissionResponse,
)

from ..security.permissions import (
    require_permission,
)

from ..models import UserTenantDB

from ..controllers import get_current_user


permission_routes = APIRouter(
    prefix="/permission",
    tags=["Permisos"],
)


# ============================================================
# LISTAR PERMISOS
# ============================================================

@permission_routes.get(
    "",
    response_model=List[PermissionResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar permisos",
    dependencies=[
        Depends(
            require_permission(
                "PERMISSION_READ"
            )
        ),
    ],
)
async def listar_permission_route(
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(
        get_current_user
    ),
):

    return listar_permisos(
        db,
    )


# ============================================================
# OBTENER PERMISO
# ============================================================

@permission_routes.get(
    "/{permission_code}",
    response_model=PermissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener permiso por código",
    dependencies=[
        Depends(
            require_permission(
                "PERMISSION_READ"
            )
        ),
    ],
)
async def obtener_permission_route(
    permission_code: str = Path(
        ...,
        description="Código del permiso",
    ),
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(
        get_current_user
    ),
):

    return obtener_permiso(
        permission_code,
        db,
    )


# ============================================================
# CREAR PERMISO
#
# SOLAMENTE SUPER_ADMIN GLOBAL
# ============================================================

@permission_routes.post(
    "",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear permiso",
    dependencies=[
         Depends(require_permission("PERMISSION_CREATE")),
    ],
)
async def crear_permission_route(
    datos: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(
        get_current_user
    ),
):

    return crear_permiso(
        datos=datos,
        current_user=current_user,
        db=db,
    )