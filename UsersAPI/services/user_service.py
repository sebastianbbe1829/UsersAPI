from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from UsersAPI.util.excel_utils import export_to_excel

from ..logging_config import logger
from ..models import TenantDB, UserDB, UserTenantDB
from ..repositories.user_repository import UserRepository
from ..schemas import UserCreate, UserUpdate
from .auth_service import get_password_hash


def _actor_dni(current_user: UserTenantDB | None) -> str:
    return current_user.user.dni if current_user else "bootstrap"


def _user_payload(user: UserDB, link: UserTenantDB, message: str | None = None):
    payload = {
        "dni": user.dni,
        "name": user.name,
        "email": link.email,
        "phone": link.phone,
        "status": link.status,
    }
    if message is not None:
        payload["message"] = message
    return payload


def create_user(
    user: UserCreate,
    db: Session,
    current_user: UserTenantDB | None = None,
    user_tenant: UserTenantDB | None = None,
):
    repo = UserRepository(db)
    if repo.get_by_dni(user.dni):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe",
        )

    ahora = datetime.now()
    nuevo_usuario = UserDB(
        dni=user.dni,
        name=user.name,
        created_at=ahora,
        created_by=_actor_dni(current_user),
    )

    try:
        db.add(nuevo_usuario)
        db.flush()

        tenant_id = user_tenant.tenant_id if user_tenant else None
        if tenant_id is None:
            tenant_id = (
                db.query(TenantDB.id)
                .filter(TenantDB.status == 1)
                .order_by(TenantDB.id)
                .scalar()
            )
        if tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No existe un tenant activo",
            )

        db.add(UserTenantDB(
            user_id=nuevo_usuario.id,
            tenant_id=tenant_id,
            email=user.email,
            password=get_password_hash(user.password),
            phone=user.phone,
            status=user.status,
            created_at=ahora,
            created_by=_actor_dni(current_user),
        ))
        db.commit()
        db.refresh(nuevo_usuario)
        link = _tenant_link(nuevo_usuario, tenant_id, db)
        return _user_payload(nuevo_usuario, link)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe",
        ) from exc


def list_users(
    db: Session,
    tenant_id: int,
    status_filter: int | None = None,
):
    users = UserRepository(db).get_all_by_tenant(tenant_id, status_filter)
    logger.debug(
        "Usuarios consultados por tenant",
        extra={"tenant_id": tenant_id, "cantidad": len(users)},
    )
    return [
        _user_payload(user, _tenant_link(user, tenant_id, db))
        for user in users
    ]


def _get_user_entity(dni: str, db: Session, tenant_id: int) -> UserDB:
    usuario = (
        db.query(UserDB)
        .join(UserTenantDB, UserTenantDB.user_id == UserDB.id)
        .filter(
            UserDB.dni == dni,
            UserTenantDB.tenant_id == tenant_id,
            UserTenantDB.status != 3,
        )
        .first()
    )
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    return usuario


def get_user(dni: str, db: Session, tenant_id: int):
    usuario = _get_user_entity(dni, db, tenant_id)
    return _user_payload(usuario, _tenant_link(usuario, tenant_id, db))


def _tenant_link(user: UserDB, tenant_id: int, db: Session) -> UserTenantDB:
    link = (
        db.query(UserTenantDB)
        .filter(
            UserTenantDB.user_id == user.id,
            UserTenantDB.tenant_id == tenant_id,
        )
        .first()
    )
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no pertenece al tenant",
        )
    return link


def update_user(
    dni: str,
    datos: UserUpdate,
    db: Session,
    current_user: UserTenantDB,
    user_tenant: UserTenantDB,
):
    usuario = _get_user_entity(dni, db, user_tenant.tenant_id)
    link = _tenant_link(usuario, user_tenant.tenant_id, db)
    cambios = datos.model_dump(exclude_unset=True)
    if "name" in cambios:
        usuario.name = cambios["name"]
    for campo in ("email", "phone", "status"):
        if campo in cambios:
            setattr(link, campo, cambios[campo])
    if cambios.get("password") is not None:
        link.password = get_password_hash(cambios["password"])
    usuario.updated_at = datetime.now()
    usuario.updated_by = current_user.user.dni
    db.commit()
    db.refresh(usuario)
    return _user_payload(usuario, link)


def delete_user(dni: str, db: Session, tenant_id: int):
    usuario = _get_user_entity(dni, db, tenant_id)
    link = _tenant_link(usuario, tenant_id, db)
    link.status = 3
    db.commit()
    return _user_payload(
        usuario,
        link,
        message="Usuario eliminado correctamente",
    )


def export_users(db: Session, current_user: UserTenantDB, tenant_id: int):
    users = list_users(db, tenant_id)
    data = []
    for user in users:
        link = _tenant_link(user, tenant_id, db)
        data.append({
            "DNI": user.dni,
            "Nombre": user.name,
            "Email": link.email,
            "Teléfono": link.phone or "",
            "Estado": "Activo" if link.status == 1 else "Inactivo",
        })
    return export_to_excel(data, "usuarios.xlsx", current_user.user)
