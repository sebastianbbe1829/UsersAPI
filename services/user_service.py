from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import UserDB
from ..repositories.user_repository import UserRepository
from ..schemas import UserCreate, UserUpdate
from .auth_service import get_password_hash
from datetime import datetime


def create_user(user: UserCreate, db: Session, current_user: UserDB | None = None) -> UserDB:
    repo = UserRepository(db)
    nuevo = UserDB(
        dni=user.dni,
        name=user.name,
        email=user.email,
        status=user.status,
        phone=user.phone,
        password=get_password_hash(user.password),
        created_by=(current_user.email if current_user is not None else "bootstrap"),
        created_at=datetime.now(),
    )
    try:
        creado = repo.add(nuevo)
        logger.info("Usuario creado", extra={"user_id": creado.id, "dni": creado.dni})
        return creado
    except IntegrityError:
        db.rollback()
        logger.warning("Error al crear usuario", extra={"email": user.email, "dni": user.dni})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe o el email ya está registrado",
        ) from None
    except Exception as exc:
        db.rollback()
        logger.error("Error inesperado al crear usuario: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear usuario",
        ) from exc


def list_users(db: Session, status_filter: int | None = None):
    repo = UserRepository(db)
    usuarios = repo.get_all(status_filter)
    logger.debug("Listando usuarios", extra={"count": len(usuarios), "status_filter": status_filter})
    return usuarios


def get_user(dni: str, db: Session):
    repo = UserRepository(db)
    usuario = repo.get_by_dni(dni)
    if not usuario:
        logger.warning("Usuario no encontrado al obtener", extra={"dni": dni})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    logger.debug("Usuario obtenido", extra={"dni": dni})
    return usuario


def update_user(dni: str, datos: UserUpdate, db: Session, current_user: UserDB | None = None)-> UserDB:
    repo = UserRepository(db)
    usuario = repo.get_by_dni(dni)
    if not usuario:
        logger.warning("Usuario no encontrado al actualizar", extra={"dni": dni})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    if datos.name is not None:
        usuario.name = datos.name
    if datos.email is not None:
        usuario.email = datos.email
    if datos.status is not None:
        usuario.status = datos.status
    if datos.phone is not None:
        usuario.phone = datos.phone
    if datos.password is not None:
        usuario.password = get_password_hash(datos.password)

    # Actualizar auditoría
    usuario.updated_by = (current_user.email if current_user is not None else "bootstrap")
    usuario.updated_at = datetime.now()

    try:
        user = repo.update(usuario)
        logger.info("Usuario actualizado", extra={"user_id": user.id, "dni": user.dni, "email": user.email})
        return user
    except IntegrityError:
        db.rollback()
        logger.warning("Error al actualizar usuario: email duplicado", extra={"dni": dni, "email": datos.email})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe o el email ya está registrado",
        ) from None


def delete_user(dni: str, db: Session):
    repo = UserRepository(db)
    usuario = repo.get_by_dni(dni)
    if not usuario:
        logger.warning("Usuario no encontrado al eliminar", extra={"dni": dni})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    repo.delete(usuario)  # Soft delete: cambia estado a 3
    logger.info("Usuario eliminado (soft delete)", extra={"user_id": usuario.id, "dni": dni, "status": usuario.status})
    return {
        "dni": usuario.dni,
        "name": usuario.name,
        "email": usuario.email,
        "status": usuario.status,  # Ahora será 3
        "phone": usuario.phone,
        "message": "Usuario eliminado correctamente",
    }
