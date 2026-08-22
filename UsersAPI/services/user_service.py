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
from ..repositories.tenant_repository import TenantRepository


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
# CREAR / REACTIVAR USUARIO
#
# POST /users
#
# REGLAS MULTITENANT:
#
#   1. El DNI puede existir en diferentes tenants.
#   2. Dentro del mismo tenant, el DNI solo puede existir una vez.
#   3. El email puede existir en diferentes tenants.
#   4. Dentro del mismo tenant, el email solo puede existir una vez.
#
# COMPORTAMIENTO:
#
#   DNI NO existe globalmente:
#       -> crea UserDB
#       -> crea UserTenantDB
#
#   DNI existe globalmente y NO pertenece al tenant:
#       -> reutiliza UserDB
#       -> crea UserTenantDB
#
#   DNI existe globalmente y pertenece al tenant:
#
#       status 0 o 1:
#           -> ERROR 409
#
#       status 3:
#           -> REACTIVA la relación existente
#           -> NO crea otro UserTenantDB
#           -> genera nuevo activation_token
#           -> actualiza email/password/phone
#           -> envía nuevamente correo de bienvenida
#           -> envía nuevamente WhatsApp
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
    tenant_repository = TenantRepository(db)

    # ========================================================
    # VALIDAR CONTEXTO TENANT
    # ========================================================

    if user_tenant is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No existe un tenant asociado al contexto actual",
        )

    tenant_id = user_tenant.tenant_id

    tenant = tenant_repository.get_by_id(
        tenant_id= tenant_id
        )

    if tenant is None:
        raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Tenant no encontrado",
        )

    tenant_slug = tenant.slug

    # ========================================================
    # ACTOR
    # ========================================================

    actor = _actor_dni(current_user)

    # ========================================================
    # BUSCAR DNI GLOBAL
    # ========================================================

    existente = user_repository.get_by_dni(
        user.dni
    )

    nuevo_usuario: UserDB

    # ========================================================
    # CASO 1:
    #
    # EL USUARIO GLOBAL YA EXISTE
    # ========================================================

    if existente is not None:

        nuevo_usuario = existente

        # ====================================================
        # BUSCAR RELACIÓN INCLUYENDO ELIMINADOS
        #
        # IMPORTANTE:
        #
        # get_by_user_and_tenant() excluye status=3.
        #
        # Aquí necesitamos saber si la relación eliminada
        # ya existe físicamente para poder REUTILIZARLA.
        # ====================================================

        link_existente = (
            user_tenant_repository
            .get_by_user_and_tenant_including_deleted(
                existente.id,
                tenant_id,
            )
        )

        # ====================================================
        # CASO 1A:
        #
        # NO EXISTE RELACIÓN CON ESTE TENANT
        #
        # El usuario existe globalmente pero pertenece
        # únicamente a otro tenant.
        #
        # Creamos una NUEVA relación.
        # ====================================================

        if link_existente is None:

            logger.info(
                "Usuario global existente será asociado "
                "a un nuevo tenant",
                extra={
                    "user_id": nuevo_usuario.id,
                    "dni": nuevo_usuario.dni,
                    "tenant_id": tenant_id,
                },
            )

            # ------------------------------------------------
            # Generar token
            # ------------------------------------------------

            activation_token = str(
                uuid.uuid4()
            )

            ahora = datetime.now()

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

            try:

                nuevo_user_tenant = (
                    user_tenant_repository.add(
                        nuevo_user_tenant
                    )
                )

            except IntegrityError as exc:

                logger.exception(
                    "Error de integridad al crear "
                    "relación usuario-tenant",
                    extra={
                        "user_id": nuevo_usuario.id,
                        "dni": nuevo_usuario.dni,
                        "tenant_id": tenant_id,
                        "email": user.email,
                    },
                )

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "El DNI o el email ya están "
                        "registrados en este tenant"
                    ),
                ) from exc

            except Exception as exc:

                logger.exception(
                    "Error inesperado al crear "
                    "relación usuario-tenant",
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

        # ====================================================
        # CASO 1B:
        #
        # YA EXISTE RELACIÓN CON ESTE TENANT
        # ====================================================

        else:

            # =================================================
            # SI ESTÁ ELIMINADO:
            #
            # REACTIVAR.
            #
            # NO INSERTAR OTRO USER_TENANT.
            # =================================================

            if link_existente.status == 3:

                logger.info(
                    "Usuario eliminado será reactivado "
                    "en el tenant",
                    extra={
                        "user_id": nuevo_usuario.id,
                        "dni": nuevo_usuario.dni,
                        "tenant_id": tenant_id,
                        "user_tenant_id": link_existente.id,
                    },
                )

                # ---------------------------------------------
                # Actualizar usuario global
                #
                # El nombre pertenece a app_users.
                # ---------------------------------------------

                nuevo_usuario.name = user.name

                # ---------------------------------------------
                # Nuevo token de activación
                # ---------------------------------------------

                activation_token = str(
                    uuid.uuid4()
                )

                ahora = datetime.now()

                # ---------------------------------------------
                # REACTIVAR RELACIÓN EXISTENTE
                # ---------------------------------------------

                link_existente.email = user.email

                link_existente.password = get_password_hash(
                    user.password
                )

                link_existente.phone = user.phone

                link_existente.activation_token = (
                    activation_token
                )

                # Volvemos al estado inicial.
                #
                # Normalmente:
                #   0 = pendiente de activación
                #
                # Esto permite que el usuario reciba
                # nuevamente el correo de bienvenida.
                link_existente.status = user.status

                link_existente.updated_at = ahora
                link_existente.updated_by = actor

                nuevo_usuario.updated_at = ahora
                nuevo_usuario.updated_by = actor

                try:

                    user_repository.update(
                        nuevo_usuario
                    )

                    user_tenant_repository.update(
                        link_existente
                    )

                except IntegrityError as exc:

                    logger.exception(
                        "Error de integridad al reactivar "
                        "usuario",
                        extra={
                            "dni": nuevo_usuario.dni,
                            "tenant_id": tenant_id,
                            "user_tenant_id": (
                                link_existente.id
                            ),
                            "email": link_existente.email,
                            "error": str(exc),
                            "orig": str(exc.orig),
                        },
                    )

                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "El DNI o el email ya están "
                            "registrados en este tenant"
                        ),
                    ) from exc

                except Exception as exc:

                    logger.exception(
                        "Error inesperado al reactivar usuario",
                        extra={
                            "dni": nuevo_usuario.dni,
                            "tenant_id": tenant_id,
                            "user_tenant_id": (
                                link_existente.id
                            ),
                        },
                    )

                    raise HTTPException(
                        status_code=(
                            status.HTTP_500_INTERNAL_SERVER_ERROR
                        ),
                        detail="Error interno al reactivar usuario",
                    ) from exc

                # ---------------------------------------------
                # La relación reutilizada pasa a ser la
                # relación actual.
                # ---------------------------------------------

                nuevo_user_tenant = link_existente

                logger.info(
                    "Usuario reactivado correctamente",
                    extra={
                        "user_id": nuevo_usuario.id,
                        "dni": nuevo_usuario.dni,
                        "tenant_id": tenant_id,
                        "user_tenant_id": (
                            nuevo_user_tenant.id
                        ),
                    },
                )

            # =================================================
            # YA EXISTE Y NO ESTÁ ELIMINADO
            # =================================================

            else:

                logger.warning(
                    "Intento de crear usuario que "
                    "ya pertenece al tenant",
                    extra={
                        "user_id": existente.id,
                        "dni": existente.dni,
                        "tenant_id": tenant_id,
                        "user_tenant_id": (
                            link_existente.id
                        ),
                        "status": link_existente.status,
                    },
                )

                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El usuario ya pertenece al tenant",
                )

    # ========================================================
    # CASO 2:
    #
    # EL DNI NO EXISTE GLOBALMENTE
    #
    # CREAMOS USERDB + USER_TENANT.
    # ========================================================

    else:

        ahora = datetime.now()

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

        except IntegrityError as exc:

            logger.exception(
                "Error de integridad al crear usuario global",
                extra={
                    "dni": user.dni,
                    "tenant_id": tenant_id,
                },
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fue posible crear el usuario",
            ) from exc

        except Exception as exc:

            logger.exception(
                "Error inesperado al crear usuario global",
                extra={
                    "dni": user.dni,
                    "tenant_id": tenant_id,
                },
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al crear usuario",
            ) from exc

        # ====================================================
        # GENERAR TOKEN
        # ====================================================

        activation_token = str(
            uuid.uuid4()
        )

        ahora = datetime.now()

        # ====================================================
        # CREAR RELACIÓN USER_TENANT
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

        try:

            nuevo_user_tenant = (
                user_tenant_repository.add(
                    nuevo_user_tenant
                )
            )

        except IntegrityError as exc:

            logger.exception(
                "Error de integridad al crear "
                "relación usuario-tenant",
                extra={
                    "user_id": nuevo_usuario.id,
                    "dni": nuevo_usuario.dni,
                    "tenant_id": tenant_id,
                    "email": user.email,
                },
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "El DNI o el email ya están "
                    "registrados en este tenant"
                ),
            ) from exc

        except Exception as exc:

            logger.exception(
                "Error inesperado al crear "
                "relación usuario-tenant",
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

    # ========================================================
    # LOG
    # ========================================================

    logger.info(
        "Usuario asociado correctamente al tenant",
        extra={
            "user_id": nuevo_usuario.id,
            "dni": nuevo_usuario.dni,
            "tenant_id": tenant_id,
            "user_tenant_id": nuevo_user_tenant.id,
        },
    )

    # ========================================================
    # EMAIL DE BIENVENIDA
    #
    # Funciona tanto para:
    #
    #   - usuario nuevo
    #   - usuario agregado a otro tenant
    #   - usuario eliminado que fue reactivado
    #
    # En los tres casos existe un NUEVO activation_token.
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
            "Usuario creado/reactivado pero falló "
            "el envío de correo: %s",
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
                        "tenant_id": tenant_id,
                    },
                )

            else:

                logger.warning(
                    "Usuario creado/reactivado correctamente, "
                    "pero WhatsApp no pudo ser enviado",
                    extra={
                        "dni": nuevo_usuario.dni,
                        "phone": nuevo_user_tenant.phone,
                        "tenant_id": tenant_id,
                    },
                )

        else:

            logger.warning(
                "Usuario creado/reactivado correctamente, "
                "pero no tiene teléfono para enviar WhatsApp",
                extra={
                    "dni": nuevo_usuario.dni,
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
    # ========================================================

    try:

        user_repository.update(
            usuario
        )

        user_tenant_repository.update(
            link
        )

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
            tenant_slug=tenant_slug,
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
    # ========================================================

    link.activation_token = None

    # ========================================================
    # AUDITORÍA
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