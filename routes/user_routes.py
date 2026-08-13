from typing import List
from fastapi import APIRouter, Body, Depends, Path, Query, Request, status, HTTPException
from sqlalchemy.orm import Session

from ..controllers import user_controller
from ..controllers.auth_controller import get_password_hash
from ..models import UserDB
from ..database import get_db
from ..controllers import get_current_user
from ..schemas import UserCreate, UserDeleteResponse, UserRead, UserUpdate

user_routes = APIRouter(
    prefix="/users",
    tags=["Usuarios"],
)

@user_routes.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario",
)
async def crear_usuario(
    user_obj: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Crear un nuevo usuario con DNI único y contraseña cifrada."""
    try:
        return user_controller.crear_usuario(user_obj, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno al crear usuario") from e

@user_routes.get(
    "",
    response_model=List[UserRead],
    status_code=status.HTTP_200_OK,
    summary="Listar usuarios",
)
async def listar_usuarios(
    status: int | None = Query(
        None,
        description="Filtra usuarios por estado (0=inactivo, 1=activo)",
        examples={  # type: ignore
            "activos": {"summary": "Usuarios activos", "value": 1},
            "inactivos": {"summary": "Usuarios inactivos", "value": 0},
        },
    ),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Listar todos los usuarios o filtrar por estado."""
    return user_controller.listar_usuarios(db, status)

@user_routes.get(
    "/{dni}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener usuario por DNI",
)
async def obtener_usuario(
    dni: str = Path(
        ...,
        description="DNI del usuario a consultar",
        examples=[{"ejemplo": {"value": "12345678"}}],
    ),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Obtener los datos de un usuario usando su DNI."""
    return user_controller.obtener_usuario(dni, db)

@user_routes.patch(
    "/{dni}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar parcialmente usuario por DNI",
)
async def actualizar_usuario(
    dni: str = Path(
        ...,
        description="DNI del usuario a actualizar",
        examples=[{"ejemplo": {"value": "12345678"}}],
    ),
    datos: UserUpdate = Body(
        ...,
        examples={  # type: ignore
            "actualizar_phone": {"summary": "Actualizar teléfono", "value": {"phone": "2781554"}},
            "actualizar_email": {"summary": "Actualizar email", "value": {"email": "juan.nuevo@example.com"}},
            "actualizar_name": {"summary": "Actualizar nombre", "value": {"name": "Juan Pérez Navarro"}},
            "actualizar_status": {"summary": "Actualizar estado", "value": {"status": False}},
        },
    ),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Actualizar los datos de un usuario identificado por DNI."""
    return user_controller.actualizar_usuario(dni, datos, db)

@user_routes.delete(
    "/{dni}",
    response_model=UserDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Eliminar usuario por DNI",
)
async def eliminar_usuario(
    dni: str = Path(
        ...,
        description="DNI del usuario a eliminar",
        examples=[{"ejemplo": {"value": "12345678"}}],
    ),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Eliminar un usuario usando su DNI."""
    return user_controller.eliminar_usuario(dni, db)
    

# Endpoint temporal para crear el primer usuario sin token
@user_routes.post(
    "/bootstrap",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario inicial sin token",
)
async def crear_usuario_inicial(
    user_obj: UserCreate,
    db: Session = Depends(get_db),
):
    return user_controller.crear_usuario(user_obj, db)