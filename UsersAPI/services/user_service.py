import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import text

from UsersAPI.util.excel_utils import export_to_excel

from ..logging_config import logger
from ..models import GlobalUserDB, UserDB, UserTenantDB
from ..repositories.user_repository import UserRepository
from ..repositories.user_tenant_repository import UserTenantRepository
from ..schemas import UserCreate, UserUpdate
from ..util.email_utils import send_email
from ..util.whatsapp_utils import send_whatsapp
from .auth_service import get_password_hash
from ..repositories.tenant_repository import TenantRepository
from ..database import set_rls_tenant


# ============================================================
# UTILIDADES
# ============================================================

def _actor_dni(
    current_user: UserTenantDB | GlobalUserDB | None,
) -> str:
    if current_user is None:
        return "bootstrap"

    if isinstance(current_user, GlobalUserDB):
        return current_user.email

    return current_user.user.dni


def _user_payload(
    user: UserDB,
    link: UserTenantDB,
    message: str | None = None,
):
    payload = {
        "dni": user.dni,
        "name": user.name,
        "email": link.email,
        "phone": link.phone,
        "status": link.status,
        "id": user.id,
    }

    if message is not None:
        payload["message"] = message

    return payload


# ============================================================
# OBTENER RELACIÓN USER_TENANT
# ============================================================

def _tenant_link(
    user: UserDB,
    tenant_id: int,
    user_tenant_repository: UserTenantRepository,
) -> UserTenantDB:
    link = user_tenant_repository.get_by_user_and_tenant(
        user.id,
        tenant_id,
    )

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no pertenece al tenant",
        )

    return link


# ============================================================
# OBTENER USUARIO POR DNI + TENANT
# ============================================================

def _get_user_entity(
    dni: str,
    tenant_id: int,
    user_repository: UserRepository,
) -> UserDB:
    usuario = user_repository.get_by_dni_in_tenant(
        dni,
        tenant_id,
    )

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    return usuario


# ============================================================
# CREAR / REACTIVAR USUARIO
# ============================================================

def create_user(
    user: UserCreate,
    db: Session,
    current_user: UserTenantDB | GlobalUserDB | None = None,
    user_tenant: UserTenantDB | None = None,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    tenant_repository = TenantRepository(db)

    if user_tenant is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No existe un tenant asociado al contexto actual",
        )

    tenant_id = user_tenant.tenant_id

    tenant = tenant_repository.get_by_id(
        tenant_id=tenant_id
    )

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )

    tenant_slug = tenant.slug
    actor = _actor_dni(current_user)

    existente = user_repository.get_by_dni(user.dni)
    nuevo_usuario: UserDB

    if existente is not None:
        nuevo_usuario = existente
        link_existente = (
            user_tenant_repository
            .get_by_user_and_tenant_including_deleted(
                existente.id,
                tenant_id,
            )
        )

        if link_existente is None:
            activation_token = str(uuid.uuid4())
            ahora = datetime.now()

            nuevo_user_tenant = UserTenantDB(
                user_id=nuevo_usuario.id,
                tenant_id=tenant_id,
                email=user.email,
                password=get_password_hash(user.password),
                phone=user.phone,
                activation_token=activation_token,
                status=user.status,
                created_at=ahora,
                created_by=actor,
            )

            try:
                nuevo_user_tenant = user_tenant_repository.add(
                    nuevo_user_tenant
                )
            except IntegrityError as exc:
                logger.exception(
                    "Error de integridad al crear relación usuario-tenant",
                    extra={
                        "user_id": nuevo_usuario.id,
                        "dni": nuevo_usuario.dni,
                        "tenant_id": tenant_id,
                        "email": user.email,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El DNI o el email ya están registrados en este tenant",
                ) from exc
            except Exception as exc:
                logger.exception(
                    "Error inesperado al crear relación usuario-tenant",
                    extra={
                        "user_id": nuevo_usuario.id,
                        "dni": nuevo_usuario.dni,
                        "tenant_id": tenant_id,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error interno al crear usuario",
                ) from exc

        else:
            if link_existente.status == 3:
                nuevo_usuario.name = user.name
                activation_token = str(uuid.uuid4())
                ahora = datetime.now()
                link_existente.email = user.email
                link_existente.password = get_password_hash(user.password)
                link_existente.phone = user.phone
                link_existente.activation_token = activation_token
                link_existente.status = user.status
                link_existente.updated_at = ahora
                link_existente.updated_by = actor
                nuevo_usuario.updated_at = ahora
                nuevo_usuario.updated_by = actor

                try:
                    user_repository.update(nuevo_usuario)
                    user_tenant_repository.update(link_existente)
                except IntegrityError as exc:
                    logger.exception(
                        "Error de integridad al reactivar usuario",
                        extra={
                            "dni": nuevo_usuario.dni,
                            "tenant_id": tenant_id,
                            "user_tenant_id": link_existente.id,
                            "email": link_existente.email,
                            "error": str(exc),
                            "orig": str(exc.orig),
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="El DNI o el email ya están registrados en este tenant",
                    ) from exc
                except Exception as exc:
                    logger.exception(
                        "Error inesperado al reactivar usuario",
                        extra={
                            "dni": nuevo_usuario.dni,
                            "tenant_id": tenant_id,
                            "user_tenant_id": link_existente.id,
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Error interno al reactivar usuario",
                    ) from exc

                nuevo_user_tenant = link_existente
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El usuario ya pertenece al tenant",
                )
    else:
        ahora = datetime.now()
        nuevo_usuario = UserDB(
            dni=user.dni,
            name=user.name,
            created_at=ahora,
            created_by=actor,
        )

        try:
            nuevo_usuario = user_repository.add(nuevo_usuario)
        except IntegrityError as exc:
            logger.exception(
                "Error de integridad al crear usuario global",
                extra={"dni": user.dni, "tenant_id": tenant_id},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fue posible crear el usuario",
            ) from exc
        except Exception as exc:
            logger.exception(
                "Error inesperado al crear usuario global",
                extra={"dni": user.dni, "tenant_id": tenant_id},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al crear usuario",
            ) from exc

        activation_token = str(uuid.uuid4())
        ahora = datetime.now()
        nuevo_user_tenant = UserTenantDB(
            user_id=nuevo_usuario.id,
            tenant_id=tenant_id,
            email=user.email,
            password=get_password_hash(user.password),
            phone=user.phone,
            activation_token=activation_token,
            status=user.status,
            created_at=ahora,
            created_by=actor,
        )

        try:
            nuevo_user_tenant = user_tenant_repository.add(nuevo_user_tenant)
        except IntegrityError as exc:
            logger.exception(
                "Error de integridad al crear relación usuario-tenant",
                extra={
                    "user_id": nuevo_usuario.id,
                    "dni": nuevo_usuario.dni,
                    "tenant_id": tenant_id,
                    "email": user.email,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El DNI o el email ya están registrados en este tenant",
            ) from exc
        except Exception as exc:
            logger.exception(
                "Error inesperado al crear relación usuario-tenant",
                extra={
                    "user_id": nuevo_usuario.id,
                    "dni": nuevo_usuario.dni,
                    "tenant_id": tenant_id,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al crear usuario",
            ) from exc

    logger.info(
        "Usuario asociado correctamente al tenant",
        extra={
            "user_id": nuevo_usuario.id,
            "dni": nuevo_usuario.dni,
            "tenant_id": tenant_id,
            "user_tenant_id": nuevo_user_tenant.id,
        },
    )

    try:
        send_email(
            recipient=nuevo_user_tenant.email,
            subject="Bienvenido a UsersAPI",
            message=(
                f"Hola {nuevo_usuario.name}, "
                "tu cuenta ha sido creada exitosamente."
            ),
            dni=nuevo_usuario.dni,
            token=nuevo_user_tenant.activation_token,
            tenant_slug=tenant_slug,
        )
        logger.info(
            "Correo de bienvenida enviado",
            extra={
                "dni": nuevo_usuario.dni,
                "email": nuevo_user_tenant.email,
                "tenant_id": tenant_id,
            },
        )
    except Exception as exc:
        logger.warning(
            "Usuario creado/reactivado pero falló el envío de correo: %s",
            exc,
        )

    try:
        if nuevo_user_tenant.phone:
            whatsapp_response = send_whatsapp(
                to_number=nuevo_user_tenant.phone,
                message=None,
                template_name="hello_world",
                parameters=None,
            )
            if whatsapp_response is not None:
                logger.info(
                    "WhatsApp de bienvenida enviado correctamente",
                    extra={
                        "dni": nuevo_usuario.dni,
                        "phone": nuevo_user_tenant.phone,
                        "tenant_id": tenant_id,
                    },
                )
    except Exception as exc:
        logger.exception(
            "Error inesperado enviando WhatsApp",
            extra={
                "dni": nuevo_usuario.dni,
                "phone": nuevo_user_tenant.phone,
                "tenant_id": tenant_id,
            },
        )

    return _user_payload(nuevo_usuario, nuevo_user_tenant)


# ============================================================
# LISTAR USUARIOS POR TENANT
# ============================================================

def list_users(
    db: Session,
    tenant_id: int,
    status_filter: int | None = None,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    users = user_repository.get_all_by_tenant(tenant_id, status_filter)
    logger.debug(
        "Usuarios consultados por tenant",
        extra={"tenant_id": tenant_id, "cantidad": len(users)},
    )
    resultado = []
    for user in users:
        link = _tenant_link(user, tenant_id, user_tenant_repository)
        resultado.append(_user_payload(user, link))
    return resultado


# ============================================================
# OBTENER USUARIO
# ============================================================

def get_user(
    dni: str,
    db: Session,
    tenant_id: int,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    usuario = _get_user_entity(dni, tenant_id, user_repository)
    link = _tenant_link(usuario, tenant_id, user_tenant_repository)
    return _user_payload(usuario, link)


# ============================================================
# ACTUALIZAR USUARIO
# ============================================================

def update_user(
    dni: str,
    datos: UserUpdate,
    db: Session,
    current_user: UserTenantDB | GlobalUserDB,
    user_tenant: UserTenantDB,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    tenant_repository = TenantRepository(db)

    tenant_id = user_tenant.tenant_id

    tenant = tenant_repository.get_by_id(
        tenant_id=tenant_id
    )

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )

    tenant_slug = tenant.slug

    usuario = _get_user_entity(dni, tenant_id, user_repository)
    link = _tenant_link(usuario, tenant_id, user_tenant_repository)

    cambios = datos.model_dump(exclude_unset=True)

    if "name" in cambios:
        usuario.name = cambios["name"]

    for campo in ("email", "phone", "status"):
        if campo in cambios:
            setattr(link, campo, cambios[campo])

    if cambios.get("password") is not None:
        link.password = get_password_hash(cambios["password"])

    ahora = datetime.now()
    actor = _actor_dni(current_user)
    usuario.updated_at = ahora
    usuario.updated_by = actor
    link.updated_at = ahora
    link.updated_by = actor

    try:
        user_repository.update(usuario)
        user_tenant_repository.update(link)
    except IntegrityError as exc:
        logger.exception(
            "Error de integridad al actualizar usuario",
            extra={
                "dni": dni,
                "tenant_id": tenant_id,
                "email": link.email,
                "error": str(exc),
                "orig": str(exc.orig),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe o el email ya está registrado",
        ) from exc
    except Exception as exc:
        logger.exception(
            "Error al actualizar usuario",
            extra={"dni": dni, "tenant_id": tenant_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar usuario",
        ) from exc

    try:
        send_email(
            recipient=link.email,
            subject="Tu cuenta en UsersAPI fue actualizada",
            message=(
                f"Hola {usuario.name}, "
                "la información de tu cuenta ha sido actualizada."
            ),
            dni=usuario.dni,
            token=link.activation_token,
            tenant_slug=tenant_slug,
        )
    except Exception as exc:
        logger.warning(
            "Usuario actualizado pero falló el envío de correo: %s",
            exc,
        )

    try:
        if link.phone:
            send_whatsapp(
                to_number=link.phone,
                message=(
                    f"Hola {usuario.name}, "
                    "tu cuenta ha sido actualizada exitosamente."
                ),
                template_name="hello_world",
                parameters=None,
            )
    except Exception as exc:
        logger.warning(
            "Usuario actualizado pero falló el envío de WhatsApp: %s",
            exc,
        )

    return _user_payload(usuario, link)


# ============================================================
# ELIMINAR USUARIO
# ============================================================

def delete_user(
    dni: str,
    db: Session,
    tenant_id: int,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    usuario = _get_user_entity(dni, tenant_id, user_repository)
    link = _tenant_link(usuario, tenant_id, user_tenant_repository)
    try:
        user_tenant_repository.delete(link)
    except Exception as exc:
        logger.exception(
            "Error al eliminar usuario",
            extra={"dni": dni, "tenant_id": tenant_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al eliminar usuario",
        ) from exc
    logger.info(
        "Usuario eliminado lógicamente",
        extra={
            "dni": dni,
            "tenant_id": tenant_id,
            "user_tenant_id": link.id,
        },
    )
    return _user_payload(
        usuario,
        link,
        message="Usuario eliminado correctamente",
    )


# ============================================================
# EXPORTAR USUARIOS
# ============================================================
def export_users(
    db: Session,
    current_user: UserTenantDB | GlobalUserDB,
    tenant_id: int,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    users = user_repository.get_all_by_tenant(tenant_id, None)
    data = []
    for user in users:
        link = _tenant_link(user, tenant_id, user_tenant_repository)
        data.append(
            {
                "DNI": user.dni,
                "Nombre": user.name,
                "Email": link.email,
                "Teléfono": link.phone or "",
                "Estado": "Activo" if link.status == 1 else "Inactivo",
            }
        )
    logger.debug(
        "Usuarios exportados",
        extra={"tenant_id": tenant_id, "cantidad": len(data)},
    )
    return export_to_excel(
        data=data,
        filename="usuarios.xlsx",
        current_user=current_user,
    )


# ============================================================
# ACTIVAR USUARIO NORMAL
#
# POST /users/activate/{dni}/{token}
# ============================================================

def activate_user(
    dni: str,
    token: str,
    db: Session,
):
    tenant_id = db.execute(
        text(
            """
            SELECT users_api.resolve_tenant_id_by_activation_token(
                :activation_token
            )
            """
        ),
        {
            "activation_token": token,
        },
    ).scalar()

    if tenant_id is None:
        logger.warning(
            "Intento de activación con token inválido",
            extra={"dni": dni},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de activación inválido",
        )

    set_rls_tenant(db, tenant_id)

    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)

    usuario = user_repository.get_by_dni(dni)

    if usuario is None:
        logger.warning(
            "Intento de activación para usuario inexistente",
            extra={"dni": dni},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    link = user_tenant_repository.get_by_activation_token(token)

    if link is None:
        logger.warning(
            "Intento de activación con token inválido",
            extra={"dni": dni},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de activación inválido",
        )

    if link.user_id != usuario.id:
        logger.warning(
            "Intento de activación con token perteneciente a otro usuario",
            extra={
                "dni": dni,
                "user_id": usuario.id,
                "token_user_id": link.user_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de activación inválido",
        )

    if link.status == 3:
        logger.warning(
            "Intento de activar usuario eliminado",
            extra={"dni": dni, "user_tenant_id": link.id},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario se encuentra eliminado",
        )

    if link.status == 1:
        logger.info(
            "Intento de activar usuario que ya estaba activo",
            extra={"dni": dni, "user_tenant_id": link.id},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario ya se encuentra activo",
        )

    link.status = 1
    link.activation_token = None

    ahora = datetime.now()
    link.updated_at = ahora
    link.updated_by = "activation"
    usuario.updated_at = ahora
    usuario.updated_by = "activation"

    try:
        user_tenant_repository.update(link)
        user_repository.update(usuario)
    except IntegrityError as exc:
        logger.exception(
            "Error de integridad al activar usuario",
            extra={
                "dni": dni,
                "user_tenant_id": link.id,
                "error": str(exc),
                "orig": str(exc.orig),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fue posible activar el usuario",
        ) from exc
    except Exception as exc:
        logger.exception(
            "Error inesperado al activar usuario",
            extra={
                "dni": dni,
                "user_tenant_id": link.id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al activar usuario",
        ) from exc

    logger.info(
        "Usuario activado correctamente",
        extra={
            "dni": dni,
            "user_id": usuario.id,
            "user_tenant_id": link.id,
        },
    )

    return _user_payload(
        usuario,
        link,
        message="Usuario activado correctamente",
    )
