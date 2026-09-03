from fastapi import APIRouter, Body, Depends, Path, status
from sqlalchemy.orm import Session

from ..controllers import user_controller
from ..dependencies import get_current_tenant, get_current_user
from ..database import get_db
from ..models.user_tenant_model import UserTenantDB
from ..schemas.user_schema import UserRead, UserUpdate
from ..security.permissions import require_permission

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/{dni}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener usuario por DNI",
    dependencies=[
        Depends(require_permission("USER_READ")),
    ],
)
async def obtener_usuario(
    dni: str = Path(
        ...,
        description="DNI del usuario a consultar",
        examples=[{"ejemplo": {"value": "12345678"}}],
    ),
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    """Obtener los datos de un usuario identificado por DNI."""

    return user_controller.obtener_usuario(
        dni,
        db,
        current_user,
        user_tenant,
    )


@router.patch(
    "/{dni}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar parcialmente usuario por DNI",
    dependencies=[
        Depends(require_permission("USER_UPDATE")),
    ],
)
async def actualizar_usuario(
    dni: str = Path(
        ...,
        description="DNI del usuario a actualizar",
        examples=[{"ejemplo": {"value": "12345678"}}],
    ),
    datos: UserUpdate = Body(
        ...,
        openapi_examples={
            "actualizar_phone": {
                "summary": "Actualizar teléfono",
                "value": {"phone": "2781554"},
            },
            "actualizar_email": {
                "summary": "Actualizar email",
                "value": {"email": "juan.nuevo@example.com"},
            },
            "actualizar_name": {
                "summary": "Actualizar nombre",
                "value": {"name": "Juan Pérez Navarro"},
            },
            "actualizar_status": {
                "summary": "Actualizar estado",
                "value": {"status": False},
            },
        },
    ),
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    """Actualizar los datos de un usuario identificado por DNI."""

    return user_controller.actualizar_usuario(
        dni,
        datos,
        db,
        current_user,
        user_tenant,
    )
