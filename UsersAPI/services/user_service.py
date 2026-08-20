import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import datetime

from UsersAPI.util.excel_utils import export_to_excel
from UsersAPI.util.whatsapp_utils import send_whatsapp

from ..logging_config import logger
from ..repositories.user_repository import UserRepository
from ..schemas import UserCreate, UserUpdate
from .auth_service import get_password_hash
from ..util import send_email
from ..models import UserDB, UserTenantDB

def create_user(user: UserCreate, db: Session, current_user: UserDB | None = None) -> UserDB:
    repo = UserRepository(db)

    # Buscar si ya existe por email o dni (incluyendo eliminados)
    existente = repo.get_by_email_or_dni(user.email, user.dni)
    token = str(uuid.uuid4())  # genera token único
    if existente:
        if existente.status == 3:  # eliminado lógico → reactivar
            existente.name = user.name
            existente.phone = user.phone
            existente.password = get_password_hash(user.password)
            existente.status = 0
            existente.activation_token = token
            existente.updated_by = current_user.email if current_user else "bootstrap"
            existente.updated_at = datetime.now()

            try:
                actualizado = repo.update(existente)
                logger.info("Usuario reactivado", extra={"user_id": actualizado.id, "dni": actualizado.dni})
            except Exception as exc:
                    db.rollback()
                    logger.error("Error inesperado al reactivar usuario: %s", exc)
                    raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error interno al reactivar usuario",
            ) from exc

            try:
                send_email(
                    recipient=actualizado.email, # pyright: ignore[reportArgumentType]
                    subject="Bienvenido nuevamente a UsersAPI",
                    message=f"Hola {actualizado.name}, tu cuenta ha sido reactivada exitosamente.",
                    dni=actualizado.dni, # pyright: ignore[reportArgumentType]
                    token=actualizado.activation_token # pyright: ignore[reportArgumentType]
                )
            except Exception as e:
                logger.warning("Usuario reactivado pero fallo al enviar correo: %s", e)

            # Enviar whatsapp de bienvenida
            try:
                send_whatsapp(to_number=user.phone, # pyright: ignore[reportArgumentType]
                              message= None,  # pyright: ignore[reportArgumentType]
                              template_name="hello_world", 
                              parameters=None # pyright: ignore[reportArgumentType]
                             )
            except Exception as e:
                        logger.warning("Usuario reactivado pero fallo al enviar mensaje de whatsapp: %s", e)

            return actualizado
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario ya existe o el email ya está registrado",
            )

    # Si no existe → crear nuevo
    nuevo_usuario = UserDB(
        dni=user.dni,
        name=user.name,
        email=user.email,
        status=user.status,
        phone=user.phone,
        activation_token=token,
        password=get_password_hash(user.password),
        created_by=(current_user.email if current_user else "bootstrap"),
        created_at=datetime.now(),
    )
    try:
        creado = repo.add(nuevo_usuario)
        logger.info("Usuario creado", extra={"user_id": creado.id, "dni": creado.dni})

        # Enviar correo de bienvenida
        try:
            send_email(
                recipient=creado.email, # pyright: ignore[reportArgumentType]
                subject="Bienvenido a UsersAPI",
                message=f"Hola {creado.name}, tu cuenta ha sido creada exitosamente.",
                dni=creado.dni, # pyright: ignore[reportArgumentType]
                token=creado.activation_token # pyright: ignore[reportArgumentType]
            )
        except Exception as e:
            logger.warning("Usuario creado pero fallo al enviar correo: %s", e)

        # Enviar whatsapp de bienvenida
        try:
            send_whatsapp(to_number=creado.phone, # pyright: ignore[reportArgumentType]
                          message= None,  # pyright: ignore[reportArgumentType]
                          template_name="hello_world", 
                          parameters=None # pyright: ignore[reportArgumentType]
                         )
        except Exception as e:
                    logger.warning("Usuario creado pero fallo al enviar mensaje de whatsapp: %s", e)

        return creado

    except IntegrityError:
        db.rollback()
        logger.warning("Error al crear usuario: email o dni duplicado", extra={"email": user.email, "dni": user.dni})
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


def list_users(
    db: Session,
    tenant_id: int,
    status_filter: int | None = None,
):
    repo = UserRepository(db)

    usuarios = repo.get_all_by_tenant(
        tenant_id=tenant_id,
        status_filter=status_filter,
    )

    logger.debug(
        "Listando usuarios por tenant",
        extra={
            "tenant_id": tenant_id,
            "count": len(usuarios),
            "status_filter": status_filter,
        },
    )

    return usuarios


def get_user(dni: str, db: Session):
    repo = UserRepository(db)
    usuario = repo.get_by_dni(dni)
    if not usuario:
        logger.warning("Usuario no encontrado al obtener", extra={"dni": dni})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    logger.debug("Usuario obtenido", extra={"dni": dni})
    return usuario


def update_user(dni: str, datos: UserUpdate, db: Session, current_user: UserDB | None = None) -> UserDB:
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

    usuario.updated_by = (current_user.email if current_user else "bootstrap")
    usuario.updated_at = datetime.now()

    try:
        actualizado = repo.update(usuario)
        logger.info("Usuario actualizado", extra={"user_id": actualizado.id, "dni": actualizado.dni, "email": actualizado.email})

        # Enviar correo de actualización
        try:
            send_email(
                recipient=actualizado.email, # pyright: ignore[reportArgumentType]
                subject="Tu cuenta en UsersAPI fue actualizada",
                message=f"Hola {actualizado.name}, la información de tu cuenta ha sido actualizada.",
                dni=actualizado.dni, # pyright: ignore[reportArgumentType]
                token=actualizado.activation_token # pyright: ignore[reportArgumentType]
            )
        except Exception as e:
            logger.warning("Usuario actualizado pero fallo al enviar correo: %s", e)

         # Enviar whatsapp de bienvenida
        try:
            send_whatsapp(
                            to_number=actualizado.phone, # pyright: ignore[reportArgumentType]
                            message=f"Hola {actualizado.name}, tu cuenta ha sido actualizada exitosamente.",
                            template_name="hello_world"  # Puedes cambiar el nombre del template según tu configuración
                        )
        except Exception as e:
            logger.warning("Usuario actualizado pero fallo al enviar mensaje de whatsapp: %s", e)

        return actualizado

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
    repo.delete(usuario)
    logger.info("Usuario eliminado (soft delete)", extra={"user_id": usuario.id, "dni": dni, "status": usuario.status})
    return {
        "dni": usuario.dni,
        "name": usuario.name,
        "email": usuario.email,
        "status": usuario.status,
        "phone": usuario.phone,
        "message": "Usuario eliminado correctamente",
    }

def activate_user(dni: str, token: str, db: Session):
    repo = UserRepository(db)
    usuario = repo.get_by_dni(dni)
    if not usuario:
        logger.warning("Usuario no encontrado al activar", extra={"dni": dni})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    
    if usuario.activation_token != token:
        logger.warning("Token de activación inválido", extra={"dni": dni, "token": token})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token de activación inválido")
    
    usuario.status = 1  # Activar el usuario
    usuario.activation_token = None  # Limpiar el token de activación
    usuario.updated_at = datetime.now()
    repo.update(usuario)
    
    logger.info("Usuario activado", extra={"user_id": usuario.id, "dni": dni})
    
    return {
        "dni": usuario.dni,
        "name": usuario.name,
        "email": usuario.email,
        "status": usuario.status,
        "phone": usuario.phone,
        "message": "Usuario activado correctamente",
    }

def export_users(db: Session, current_user: UserDB | None = None):
    repo = UserRepository(db)
    usuarios = repo.get_all()   # <- aquí debe devolver lista, no lanzar excepción

    data = [{
        "DNI": u.dni,
        "Nombre": u.name,
        "Email": u.email,
        "Teléfono": u.phone,
        "Estado": "Activo" if u.status == 1 else "Inactivo"
    } for u in usuarios]

    return export_to_excel(data, filename="Usuarios.xlsx", current_user=current_user)
