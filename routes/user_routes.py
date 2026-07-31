from typing import List

from fastapi import APIRouter, Body, Depends, Path, Query, status, Request, HTTPException
from sqlalchemy.orm import Session

from ..controllers import user_controller
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
        201: {
            "description": "Usuario creado exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "dni": "12345678",
                        "name": "Juan Pérez",
                        "email": "juan.perez@example.com",
                        "status": True,
                        "phone": "123456789",
                    }
                }
            }
        },
        400: {
            "description": "Datos inválidos o usuario/email duplicado",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "El usuario ya existe o el email ya está registrado"
                    }
                }
            }
        },
        422: {
            "description": "Error de validación de datos",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "email"],
                                "msg": "value is not a valid email address",
                                "type": "value_error.email"
                            }
                        ]
                    }
                }
            }
        },
    },
)
async def crear_usuario(
    request: Request,
    db: Session = Depends(get_db),
):
    """Crear un nuevo usuario con DNI único.

    El DNI debe ser único y el email también debe ser único en la base de datos.
    """

    user_obj = UserCreate(**await request.json())
    return user_controller.crear_usuario(user_obj, db)

@user_routes.get(
    "",
    response_model=List[UserRead],
    status_code=status.HTTP_200_OK,
    summary="Listar usuarios",
    responses={
        200: {
            "description": "Lista de usuarios obtenida",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "dni": "12345678",
                            "name": "Juan Pérez",
                            "email": "juan.perez@example.com",
                            "status": True,
                            "phone": "123456789",
                        },
                        {
                            "dni": "87654321",
                            "name": "María López",
                            "email": "maria.lopez@example.com",
                            "status": False,
                            "phone": "987654321",
                        }
                    ]
                }
            }
        },
        400: {
            "description": "Solicitud inválida",
            "content": {
                "application/json": {
                    "example": {"detail": "Parámetro de consulta inválido"}
                }
            }
        },
        422: {"description": "Error de validación de parámetros"},
    },
)
async def listar_usuarios(
    status: bool | None = Query(
        None,
        description="Filtra usuarios por estado activo (true) o inactivo (false)",
        examples={
            "activos": {
                "summary": "Usuarios activos",
                "description": "Filtra para devolver solo los usuarios activos.",
                "value": True,
            },
            "inactivos": {
                "summary": "Usuarios inactivos",
                "description": "Filtra para devolver solo los usuarios inactivos.",
                "value": False,
            },
        },
    ),
    db: Session = Depends(get_db),
):
    """Listar todos los usuarios o filtrar por estado."""
    return user_controller.listar_usuarios(db, status)


@user_routes.get(
    "/{dni}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener usuario por DNI",
    responses={
        200: {
            "description": "Usuario encontrado",
            "content": {
                "application/json": {
                    "example": {
                        "dni": "12345678",
                        "name": "Juan Pérez",
                        "email": "juan.perez@example.com",
                        "status": True,
                        "phone": "123456789",
                    }
                }
            }
        },
        400: {
            "description": "Solicitud inválida",
            "content": {
                "application/json": {
                    "example": {"detail": "Solicitud inválida"}
                }
            }
        },
        404: {
            "description": "Usuario no encontrado",
            "content": {
                "application/json": {
                    "example": {"detail": "Usuario no encontrado"}
                }
            }
        },
        422: {
            "description": "DNI inválido",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["path", "dni"],
                                "msg": "string does not match regex \"^[0-9]+\\$\"",
                                "type": "value_error.str.regex"
                            }
                        ]
                    }
                }
            }
        },
    },
)
async def obtener_usuario(
    dni: str = Path(
        ..., 
        description="DNI del usuario a consultar",
        examples={"ejemplo": {"value": "12345678"}},
    ),
    db: Session = Depends(get_db),
):
    """Obtener los datos de un usuario usando su DNI."""
    return user_controller.obtener_usuario(dni, db)

@user_routes.patch(
    "/{dni}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar parcialmente usuario por DNI",
    description="Actualiza uno o más campos del usuario identificado por DNI sin requerir todos los campos en el cuerpo de la solicitud.",
    responses={
        200: {
            "description": "Usuario actualizado",
            "content": {
                "application/json": {
                    "example": {
                        "dni": "12345678",
                        "name": "Juan Pérez Actualizado",
                        "email": "juan.actualizado@example.com",
                        "status": False,
                        "phone": "987654321",
                    }
                }
            }
        },
        400: {
            "description": "Datos inválidos o dni/email duplicado",
            "content": {
                "application/json": {
                    "example": {"detail": "El usuario ya existe o el email ya está registrado"}
                }
            }
        },
        404: {
            "description": "Usuario no encontrado",
            "content": {
                "application/json": {
                    "example": {"detail": "Usuario no encontrado"}
                }
            }
        },
        422: {
            "description": "Error de validación de datos",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "email"],
                                "msg": "value is not a valid email address",
                                "type": "value_error.email"
                            }
                        ]
                    }
                }
            }
        },
    },
)
async def actualizar_usuario(
    dni: str = Path(
        ..., 
        description="DNI del usuario a actualizar",
        examples={"ejemplo": {"value": "12345678"}},
    ),
    datos: UserUpdate = Body(
        ...,
        examples={
            "actualizar_phone": {
                "summary": "Actualizar solo el teléfono",
                "description": "Solo enviar el campo que se desea actualizar, por ejemplo el teléfono.",
                "value": {
                    "phone": "2781554",
                },
            },
            "actualizar_email": {
                "summary": "Actualizar email",
                "description": "Enviar únicamente el nuevo email si solo se quiere cambiar ese campo.",
                "value": {
                    "email": "juan.nuevo@example.com",
                },
            },
            "actualizar_name": {
                "summary": "Actualizar solo el nombre",
                "description": "Enviar únicamente el nuevo nombre si solo se quiere cambiar ese campo.",
                "value": {
                    "name": "Juan Pérez Navarro",
                },
            },
            "actualizar_status": {
                "summary": "Actualizar solo el estado",
                "description": "Enviar únicamente el estado si solo quiere activar o desactivar al usuario.",
                "value": {
                    "status": False,
                },
            },
        },
    ),
    db: Session = Depends(get_db),
):
    """Actualizar los datos de un usuario identificado por DNI."""
    return user_controller.actualizar_usuario(dni, datos, db)

@user_routes.delete(
    "/{dni}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar usuario por DNI",
    responses={
        204: {"description": "Usuario eliminado correctamente"},
        400: {
            "description": "Solicitud inválida",
            "content": {
                "application/json": {
                    "example": {"detail": "DNI no proporcionado o inválido"}
                }
            }
        },
        404: {
            "description": "Usuario no encontrado",
            "content": {
                "application/json": {
                    "example": {"detail": "Usuario no encontrado"}
                }
            }
        },
        422: {
            "description": "DNI inválido",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["path", "dni"],
                                "msg": "string does not match regex \"^[0-9]+\\$\"",
                                "type": "value_error.str.regex"
                            }
                        ]
                    }
                }
            }
        },
    },
)
async def eliminar_usuario(
    dni: str = Path(
        ..., 
        description="DNI del usuario a eliminar",
        examples={"ejemplo": {"value": "12345678"}},
    ),
    db: Session = Depends(get_db),
):
    """Eliminar un usuario usando su DNI."""
    user_controller.eliminar_usuario(dni, db)
    return
