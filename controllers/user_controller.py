from sqlalchemy.orm import Session

from ..models.user import UserDB

from ..schemas import UserCreate, UserUpdate
from ..services.user_service import create_user, delete_user, export_users, get_user, list_users, update_user, activate_user


def crear_usuario(user: UserCreate, db: Session, current_user: UserDB | None = None):
    return create_user(user, db, current_user)


def listar_usuarios(db: Session, status: int | None = None):
    return list_users(db, status)


def obtener_usuario(dni: str, db: Session):
    return get_user(dni, db)


def actualizar_usuario(dni: str, datos: UserUpdate, db: Session, current_user: UserDB | None = None):
    return update_user(dni, datos, db, current_user)


def eliminar_usuario(dni: str, db: Session):
    return delete_user(dni, db)

def activar_usuario(dni: str, token: str, db: Session):
    return activate_user(dni, token, db)

def exportar_usuarios(db: Session, current_user: UserDB | None = None):
    return export_users(db,current_user)    