from sqlalchemy.orm import Session

from ..models.user import UserDB

from ..schemas import UserCreate, UserUpdate
from ..services.user_service import create_user, delete_user, get_user, list_users, update_user


def crear_usuario(user: UserCreate, db: Session, current_user: UserDB | None = None):
    return create_user(user, db, current_user)


def listar_usuarios(db: Session, status: int | None = None):
    return list_users(db, status)


def obtener_usuario(dni: str, db: Session):
    return get_user(dni, db)


def actualizar_usuario(dni: str, datos: UserUpdate, db: Session):
    return update_user(dni, datos, db)


def eliminar_usuario(dni: str, db: Session):
    return delete_user(dni, db)
