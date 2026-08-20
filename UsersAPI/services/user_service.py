import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from UsersAPI.util.excel_utils import export_to_excel

from ..logging_config import logger
from ..models import UserDB, UserTenantDB
from ..repositories.user_repository import UserRepository
from ..repositories.user_tenant_repository import UserTenantRepository
from ..schemas import UserCreate, UserUpdate
from ..util.email_utils import send_email
from ..util.whatsapp_utils import send_whatsapp
from .auth_service import get_password_hash


# ============================================================
# UTILIDADES
# ============================================================

def _actor_dni(
    current_user: UserTenantDB | None,
) -> str:
    """
    Obtiene el DNI del usuario que ejecuta la operación.

    Para bootstrap no existe usuario autenticado.
    """

    return (
        current_user.user.dni
        if current_user
        else "bootstrap"
    )


def _user_payload(
    user: UserDB,
    link: UserTenantDB,
    message: str | None = None,
):
    """
    Construye la respuesta pública del usuario.

    Nunca expone:
        - password
        - activation_token
        - IDs internos
    """

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


# ============================================================
# OBTENER RELACIÓN USER_TENANT
# ============================================================

def _tenant_link(
    user: UserDB,
    tenant_id: int,
    user_tenant_repository: UserTenantRepository,
) -> UserTenantDB:
    """
    Obtiene la relación entre UserDB y TenantDB.
    """

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
    """
    Obtiene un usuario global únicamente si pertenece
    al tenant indicado y su relación no está eliminada.
    """

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
# CREAR USUARIO
#
# POST /users
#
# CREA:
#
#   1. app_users
#   2. user_tenants
#
# IMPORTANTE:
#
# Este service NO hace:
#
#   db.commit()
#   db.rollback()
#
# La transacción es responsabilidad de database.py.
# ============================================================

def create_user(
    user: UserCreate,
    db: Session,
    current_user: UserTenantDB | None = None,
    user_tenant: UserTenantDB | None = None,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)

    # ========================================================
    # VALIDAR CONTEXTO TENANT
    # ========================================================

    if user_tenant is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No existe un tenant asociado al contexto actual",
        )

    tenant_id = user_tenant.tenant_id

    # ========================================================
    # ACTOR
    # ========================================================

    actor = _actor_dni(current_user)

    # ========================================================
    # VALIDAR DNI GLOBAL
    # ========================================================

    existente = user_repository.get_by_dni(
        user.dni
    )

    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe",
        )

    # ========================================================
    # GENERAR TOKEN DE ACTIVACIÓN
    #
    # El token pertenece a user_tenants porque:
    #
    # email
    # password
    # phone
    # activation_token
    #
    # pertenecen a la relación usuario-tenant.
    # ========================================================

    activation_token = str(
        uuid.uuid4()
    )

    ahora = datetime.now()

    # ========================================================
    # CREAR USERDB
    # ========================================================

    nuevo_usuario = UserDB(
        dni=user.dni,
        name=user.name,
        created_at=ahora,
        created_by=actor,
    )

    try:

        nuevo_usuario = user_repository.add(
            nuevo_usuario
        )

        # ====================================================
        # CREAR USER_TENANT
        # ====================================================

        nuevo_user_tenant = UserTenantDB(
            user_id=nuevo_usuario.id,
            tenant_id=tenant_id,
            email=user.email,
            password=get_password_hash(
                user.password
            ),
            phone=user.phone,
            activation_token=activation_token,
            status=user.status,
            created_at=ahora,
            created_by=actor,
        )

        nuevo_user_tenant = (
            user_tenant_repository.add(
                nuevo_user_tenant
            )
        )

    except IntegrityError as exc:

        logger.warning(
            "Error de integridad al crear usuario",
            extra={
                "dni": user.dni,
                "tenant_id": tenant_id,
            },
        )

        # IMPORTANTE:
        #
        # NO hacemos db.rollback() aquí.
        #
        # database.py será responsable del rollback.
        #

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe",
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "Error inesperado al crear usuario",
            extra={
                "dni": user.dni,
                "tenant_id": tenant_id,
            },
        )

        # NO rollback aquí.
        # database.py controla la transacción.

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear usuario",
        ) from exc

    # ========================================================
    # LOG
    # ========================================================

    logger.info(
        "Usuario creado correctamente en la sesión",
        extra={
            "user_id": nuevo_usuario.id,
            "dni": nuevo_usuario.dni,
            "tenant_id": tenant_id,
        },
    )

    # ========================================================
    # EMAIL
    #
    # IMPORTANTE:
    #
    # El envío NO debe impedir la creación del usuario.
    #
    # Si el correo falla:
    #   - se registra warning
    #   - la operación continúa
    #
    # NO hacemos rollback por fallo de correo.
    # ========================================================

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
        )

        logger.info(
            "Correo de bienvenida enviado",
            extra={
                "dni": nuevo_usuario.dni,
                "email": nuevo_user_tenant.email,
            },
        )

    except Exception as exc:

        logger.warning(
            "Usuario creado pero falló el envío de correo: %s",
            exc,
        )

    # ========================================================
    # WHATSAPP
    # ========================================================

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
                    },
                )

            else:

                logger.warning(
                    "Usuario creado correctamente, "
                    "pero WhatsApp no pudo ser enviado",
                    extra={
                        "dni": nuevo_usuario.dni,
                        "phone": nuevo_user_tenant.phone,
                    },
                )

        else:

            logger.warning(
                "Usuario creado correctamente, "
                "pero no tiene teléfono para enviar WhatsApp",
                extra={
                    "dni": nuevo_usuario.dni,
                },
            )

    except Exception as exc:

        logger.exception(
            "Error inesperado enviando WhatsApp",
            extra={
                "dni": nuevo_usuario.dni,
                "phone": nuevo_user_tenant.phone,
            },
    )

    # ========================================================
    # RESPUESTA
    # ========================================================

    return _user_payload(
        nuevo_usuario,
        nuevo_user_tenant,
    )

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

    users = user_repository.get_all_by_tenant(
        tenant_id,
        status_filter,
    )

    logger.debug(
        "Usuarios consultados por tenant",
        extra={
            "tenant_id": tenant_id,
            "cantidad": len(users),
        },
    )

    resultado = []

    for user in users:

        link = _tenant_link(
            user,
            tenant_id,
            user_tenant_repository,
        )

        resultado.append(
            _user_payload(
                user,
                link,
            )
        )

    return resultado


# ============================================================
# OBTENER USUARIO
#
# GET /users/{dni}
# ============================================================

def get_user(
    dni: str,
    db: Session,
    tenant_id: int,
):

    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)

    usuario = _get_user_entity(
        dni,
        tenant_id,
        user_repository,
    )

    link = _tenant_link(
        usuario,
        tenant_id,
        user_tenant_repository,
    )

    return _user_payload(
        usuario,
        link,
    )


# ============================================================
# ACTUALIZAR USUARIO
#
# PATCH /users/{dni}
#
# NO COMMIT
# NO ROLLBACK
# ============================================================

def update_user(
    dni: str,
    datos: UserUpdate,
    db: Session,
    current_user: UserTenantDB,
    user_tenant: UserTenantDB,
):

    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)

    tenant_id = user_tenant.tenant_id

    # ========================================================
    # BUSCAR USUARIO
    # ========================================================

    usuario = _get_user_entity(
        dni,
        tenant_id,
        user_repository,
    )

    # ========================================================
    # BUSCAR RELACIÓN
    # ========================================================

    link = _tenant_link(
        usuario,
        tenant_id,
        user_tenant_repository,
    )

    # ========================================================
    # OBTENER CAMBIOS
    # ========================================================

    cambios = datos.model_dump(
        exclude_unset=True,
    )

    # ========================================================
    # ACTUALIZAR USERDB
    # ========================================================

    if "name" in cambios:
        usuario.name = cambios["name"]

    # ========================================================
    # ACTUALIZAR USER_TENANTS
    # ========================================================

    for campo in (
        "email",
        "phone",
        "status",
    ):
        if campo in cambios:
            setattr(
                link,
                campo,
                cambios[campo],
            )

    # ========================================================
    # PASSWORD
    # ========================================================

    if cambios.get("password") is not None:

        link.password = get_password_hash(
            cambios["password"]
        )

    # ========================================================
    # AUDITORÍA
    # ========================================================

    ahora = datetime.now()
    actor = current_user.user.dni

    usuario.updated_at = ahora
    usuario.updated_by = actor

    link.updated_at = ahora
    link.updated_by = actor

    # ========================================================
    # PERSISTIR EN LA SESIÓN
    #
    # Los repositories hacen flush.
    #
    # NO COMMIT.
    # ========================================================

    try:

        user_repository.update(
            usuario
        )

        user_tenant_repository.update(
            link
        )

    except IntegrityError as exc:

        logger.warning(
            "Error de integridad al actualizar usuario",
            extra={
                "dni": dni,
                "tenant_id": tenant_id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "El usuario ya existe o "
                "el email ya está registrado"
            ),
        ) from exc

    except Exception as exc:

        logger.exception(
            "Error al actualizar usuario",
            extra={
                "dni": dni,
                "tenant_id": tenant_id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar usuario",
        ) from exc

    # ========================================================
    # EMAIL
    # ========================================================

    try:

        send_email(
            recipient=link.email,
            subject="Tu cuenta en UsersAPI fue actualizada",
            message=(
                f"Hola {usuario.name}, "
                "la información de tu cuenta "
                "ha sido actualizada."
            ),
            dni=usuario.dni,
            token=link.activation_token,
        )

    except Exception as exc:

        logger.warning(
            "Usuario actualizado pero falló "
            "el envío de correo: %s",
            exc,
        )

    # ========================================================
    # WHATSAPP
    # ========================================================

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
            "Usuario actualizado pero falló "
            "el envío de WhatsApp: %s",
            exc,
        )

    return _user_payload(
        usuario,
        link,
    )


# ============================================================
# ELIMINAR USUARIO
#
# DELETE /users/{dni}
#
# NO COMMIT
# ============================================================

def delete_user(
    dni: str,
    db: Session,
    tenant_id: int,
):

    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)

    # ========================================================
    # BUSCAR USUARIO
    # ========================================================

    usuario = _get_user_entity(
        dni,
        tenant_id,
        user_repository,
    )

    # ========================================================
    # BUSCAR RELACIÓN
    # ========================================================

    link = _tenant_link(
        usuario,
        tenant_id,
        user_tenant_repository,
    )

    # ========================================================
    # ELIMINACIÓN LÓGICA
    # ========================================================

    try:

        user_tenant_repository.delete(
            link
        )

    except Exception as exc:

        logger.exception(
            "Error al eliminar usuario",
            extra={
                "dni": dni,
                "tenant_id": tenant_id,
            },
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
#
# GET /users/export
# ============================================================

def export_users(
    db: Session,
    current_user: UserTenantDB,
    tenant_id: int,
):

    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)

    # ========================================================
    # OBTENER USUARIOS
    # ========================================================

    users = user_repository.get_all_by_tenant(
        tenant_id,
        None,
    )

    data = []

    for user in users:

        link = _tenant_link(
            user,
            tenant_id,
            user_tenant_repository,
        )

        data.append(
            {
                "DNI": user.dni,
                "Nombre": user.name,
                "Email": link.email,
                "Teléfono": link.phone or "",
                "Estado": (
                    "Activo"
                    if link.status == 1
                    else "Inactivo"
                ),
            }
        )

    logger.debug(
        "Usuarios exportados",
        extra={
            "tenant_id": tenant_id,
            "cantidad": len(data),
            "usuario_exportador": current_user.user.dni,
        },
    )

    return export_to_excel(
        data,
        "usuarios.xlsx",
        current_user.user,
    )

# ============================================================
# ACTIVAR USUARIO
#
# POST /users/activate/{dni}/{token}
#
# La activación:
#
#   1. Valida el DNI.
#   2. Valida el activation_token.
#   3. Verifica que el token pertenece al usuario.
#   4. Cambia status: 0 -> 1.
#   5. Invalida el activation_token.
#
# NO COMMIT
# NO ROLLBACK
#
# La transacción es responsabilidad de database.py.
# ============================================================

def activate_user(
    dni: str,
    token: str,
    db: Session,
):

    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)

    # ========================================================
    # BUSCAR USUARIO POR DNI
    #
    # Aquí usamos get_by_dni(), porque el usuario todavía
    # puede estar inactivo.
    # ========================================================

    usuario = user_repository.get_by_dni(dni)

    if usuario is None:

        logger.warning(
            "Intento de activación para usuario inexistente",
            extra={
                "dni": dni,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    # ========================================================
    # BUSCAR ACTIVATION TOKEN
    # ========================================================

    link = user_tenant_repository.get_by_activation_token(
        token
    )

    if link is None:

        logger.warning(
            "Intento de activación con token inválido",
            extra={
                "dni": dni,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de activación inválido",
        )

    # ========================================================
    # VALIDAR QUE EL TOKEN PERTENECE AL USUARIO
    # ========================================================

    if link.user_id != usuario.id:

        logger.warning(
            "Intento de activación con token "
            "perteneciente a otro usuario",
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

    # ========================================================
    # VALIDAR USUARIO ELIMINADO
    # ========================================================

    if link.status == 3:

        logger.warning(
            "Intento de activar usuario eliminado",
            extra={
                "dni": dni,
                "user_tenant_id": link.id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario se encuentra eliminado",
        )

    # ========================================================
    # VALIDAR SI YA ESTÁ ACTIVO
    # ========================================================

    if link.status == 1:

        logger.info(
            "Intento de activar usuario que ya estaba activo",
            extra={
                "dni": dni,
                "user_tenant_id": link.id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario ya se encuentra activo",
        )

    # ========================================================
    # ACTIVAR
    # ========================================================

    link.status = 1

    # ========================================================
    # INVALIDAR TOKEN
    #
    # Esto es MUY importante.
    #
    # El enlace de activación debe ser de un solo uso.
    # ========================================================

    link.activation_token = None

    # ========================================================
    # AUDITORÍA
    #
    # La activación viene desde un enlace de correo,
    # por lo tanto no existe current_user autenticado.
    # ========================================================

    ahora = datetime.now()

    link.updated_at = ahora
    link.updated_by = "activation"

    usuario.updated_at = ahora
    usuario.updated_by = "activation"

    # ========================================================
    # PERSISTIR
    # ========================================================

    try:

        user_tenant_repository.update(
            link
        )

        user_repository.update(
            usuario
        )

    except IntegrityError as exc:

        logger.warning(
            "Error de integridad al activar usuario",
            extra={
                "dni": dni,
                "user_tenant_id": link.id,
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

    # ========================================================
    # LOG
    # ========================================================

    logger.info(
        "Usuario activado correctamente",
        extra={
            "dni": dni,
            "user_id": usuario.id,
            "user_tenant_id": link.id,
        },
    )

    # ========================================================
    # RESPUESTA
    # ========================================================

    return _user_payload(
        usuario,
        link,
        message="Usuario activado correctamente",
    )