from typing import List
from fastapi import APIRouter, Body, Depends, Path, Query, status, Request
from sqlalchemy.orm import Session

from ..controllers import user_controller
from ..auth import get_current_user
from ..models import UserDB
from ..database import get_db
from ..schemas import UserCreate, UserRead, UserUpdate

user_routes = APIRouter(
    prefix="/users",
    tags=["Usuarios"],
)

@user_routes.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario",
    responses={
        201: {"description": "Usuario creado exitosamente"},
        400: {"description": "Datos inválidos o usuario/email duplicado"},
        422: {"description": "Error de validación de datos"},
    },
)
async def crear_usuario(
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Crear un nuevo usuario con DNI único."""
    user_obj = UserCreate(**await request.json())
    return user_controller.crear_usuario(user_obj, db)

@user_routes.get(
    "",
    response_model=List[UserRead],
    status_code=status.HTTP_200_OK,
    summary="Listar usuarios",
)
async def listar_usuarios(
    status: bool | None = Query(
        None,
        description="Filtra usuarios por estado activo (true) o inactivo (false)",
        examples={  # type: ignore
            "activos": {"summary": "Usuarios activos", "value": True},
            "inactivos": {"summary": "Usuarios inactivos", "value": False},
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
        example="12345678",  # ✅ usar example en lugar de examples
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
        example="12345678",
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
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar usuario por DNI",
)
async def eliminar_usuario(
    dni: str = Path(
        ...,
        description="DNI del usuario a eliminar",
        example="12345678",
    ),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Eliminar un usuario usando su DNI."""
    user_controller.eliminar_usuario(dni, db)
    return
