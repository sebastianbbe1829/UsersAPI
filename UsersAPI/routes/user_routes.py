from typing import List, cast

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Path,
    Query,
    status,
    HTTPException,
)
from sqlalchemy.orm import Session

from ..controllers import user_controller
from ..controllers.activation_otp_controller import (
    request_activation_otp,
    verify_activation_otp,
)
from ..database import get_db
from ..controllers import get_current_user
from ..schemas import (
    UserCreate,
    UserDeleteResponse,
    UserRead,
    UserUpdate,
)
from ..schemas.activation_otp import (
    ActivationOTPGenerateResponse,
    ActivationOTPValidateRequest,
    ActivationOTPValidateResponse,
)
from ..security.dependencies import get_current_tenant
from ..security.permissions import require_permission
from ..models import UserTenantDB


user_routes = APIRouter(
    prefix="/users",
    tags=["Usuarios"],
)


@user_routes.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario",
    dependencies=[
        Depends(require_permission("USER_CREATE")),
    ],
)
async def crear_usuario(
    user_obj: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    """Crear un nuevo usuario con DNI único y contraseña cifrada."""

    try:
        return user_controller.crear_usuario(
            user_obj,
            db,
            current_user,
            user_tenant,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear usuario",
        ) from e


@user_routes.get(
    "/export",
    response_description="Exportar usuarios a Excel",
    summary="Exportar usuarios",
    dependencies=[
        Depends(require_permission("USER_EXPORT")),
    ],
)
async def export_users_route(
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    """Exportar usuarios del tenant seleccionado a Excel."""

    return user_controller.exportar_usuarios(
        db,
        current_user,
        user_tenant,
    )


@user_routes.get(
    "",
    response_model=List[UserRead],
    status_code=status.HTTP_200_OK,
    summary="Listar usuarios",
    dependencies=[
        Depends(require_permission("USER_READ")),
    ],
)
async def listar_usuarios(
    status: int | None = Query(
        None,
        description="Filtra usuarios por estado (0=inactivo, 1=activo)",
        examples={
            "activos": {
                "summary": "Usuarios activos",
                "value": 1,
            },
            "inactivos": {
                "summary": "Usuarios inactivos",
                "value": 0,
            },
        },
    ),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    """Listar usuarios pertenecientes al tenant seleccionado."""

    return user_controller.listar_usuarios(
        db=db,
        tenant_id=cast(int, user_tenant.tenant_id),
        status_filter=status,
    )


@user_routes.get(
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
        examples=[
            {"ejemplo": {"value": "12345678"}}
        ],
    ),
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    """Obtener los datos de un usuario usando su DNI."""

    return user_controller.obtener_usuario(
        dni,
        db,
        user_tenant,
    )


@user_routes.patch(
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
        examples=[
            {"ejemplo": {"value": "12345678"}}
        ],
    ),
    datos: UserUpdate = Body(
        ...,
        examples={
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


@user_routes.delete(
    "/{dni}",
    response_model=UserDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Eliminar usuario por DNI",
    dependencies=[
        Depends(require_permission("USER_DELETE")),
    ],
)
async def eliminar_usuario(
    dni: str = Path(
        ...,
        description="DNI del usuario a eliminar",
        examples=[
            {"ejemplo": {"value": "12345678"}}
        ],
    ),
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    """Eliminar un usuario usando su DNI."""

    return user_controller.eliminar_usuario(
        dni,
        db,
        user_tenant,
    )


@user_routes.post(
    "/activate/{dni}/{token}/otp",
    response_model=ActivationOTPGenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Solicitar OTP para activar usuario",
)
async def solicitar_otp_activacion(
    dni: str = Path(..., description="DNI del usuario a activar"),
    token: str = Path(..., description="Token de activación enviado por correo"),
    db: Session = Depends(get_db),
):
    """Generar y enviar el OTP requerido para completar la activación."""

    return request_activation_otp(
        dni=dni,
        token=token,
        db=db,
    )


@user_routes.post(
    "/activate/{dni}/{token}/otp/validate",
    response_model=ActivationOTPValidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Validar OTP y activar usuario",
)
async def validar_otp_activacion(
    datos: ActivationOTPValidateRequest,
    dni: str = Path(..., description="DNI del usuario a activar"),
    token: str = Path(..., description="Token de activación enviado por correo"),
    db: Session = Depends(get_db),
):
    """Validar el OTP y activar la cuenta únicamente si el código es correcto."""

    return verify_activation_otp(
        dni=dni,
        token=token,
        datos=datos,
        db=db,
    )
