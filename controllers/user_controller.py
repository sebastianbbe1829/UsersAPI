from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..logging_config import logger
from ..models import UserDB
from ..repositories.user_repository import UserRepository
from ..schemas import UserCreate, UserUpdate
from ..controllers.auth_controller import get_password_hash

def crear_usuario(user: UserCreate, db: Session) -> UserDB:
    repo = UserRepository(db)
    nuevo = UserDB(
        dni=user.dni,
        name=user.name,
        email=user.email,
        status=user.status,
        phone=user.phone,
        password=get_password_hash(user.password)
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
            detail="El usuario ya existe o el email ya está registrado"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error inesperado al crear usuario: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear usuario"
        )


def listar_usuarios(db: Session, status: bool | None = None):
    repo = UserRepository(db)
    usuarios = repo.get_all(status)
    logger.debug("Listando usuarios", extra={"count": len(usuarios), "status_filter": status})
    return usuarios


def obtener_usuario(dni: str, db: Session):
    repo = UserRepository(db)
    usuario = repo.get_by_dni(dni)
    if not usuario:
        logger.warning("Usuario no encontrado al obtener", extra={"dni": dni})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    logger.debug("Usuario obtenido", extra={"dni": dni})
    return usuario


def actualizar_usuario(dni: str, datos: UserUpdate, db: Session):
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
        usuario.password = get_password_hash(datos.password)  # 🔒 actualizar cifrada

    try:
        user = repo.update(usuario)
        logger.info("Usuario actualizado", extra={"user_id": user.id, "dni": user.dni, "email": user.email})
        return user
    except IntegrityError:
        db.rollback()
        logger.warning("Error al actualizar usuario: email duplicado", extra={"dni": dni, "email": datos.email})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario ya existe o el email ya está registrado")


def eliminar_usuario(dni: str, db: Session):
    repo = UserRepository(db)
    usuario = repo.get_by_dni(dni)
    if not usuario:
        logger.warning("Usuario no encontrado al eliminar", extra={"dni": dni})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    repo.delete(usuario)
    logger.info("Usuario eliminado", extra={"user_id": usuario.id, "dni": dni})
