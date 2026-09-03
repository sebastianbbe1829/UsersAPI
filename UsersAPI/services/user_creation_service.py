import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import GlobalUserDB, UserDB, UserTenantDB
from ..repositories.tenant_repository import TenantRepository
from ..repositories.user_repository import UserRepository
from ..repositories.user_tenant_repository import UserTenantRepository
from ..schemas import UserCreate
from .auth_service import get_password_hash
from .user_service_helpers import _actor_dni, _user_payload
from .user_notification_service import send_user_notifications


def create_tenant_link(
    user: UserCreate,
    usuario: UserDB,
    tenant_id: int,
    actor: str,
    user_tenant_repository: UserTenantRepository,
) -> UserTenantDB:
    activation_token = str(uuid.uuid4())
    ahora = datetime.now()

    nuevo_user_tenant = UserTenantDB(
        user_id=usuario.id,
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
        return user_tenant_repository.add(nuevo_user_tenant)
    except IntegrityError as exc:
        logger.exception(
            "Error de integridad al crear relación usuario-tenant",
            extra={
                "user_id": usuario.id,
                "dni": usuario.dni,
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
                "user_id": usuario.id,
                "dni": usuario.dni,
                "tenant_id": tenant_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear usuario",
        ) from exc


def reactivate_user(
    user: UserCreate,
    usuario: UserDB,
    link_existente: UserTenantDB,
    tenant_id: int,
    actor: str,
    user_repository: UserRepository,
    user_tenant_repository: UserTenantRepository,
) -> UserTenantDB:
    usuario.name = user.name
    activation_token = str(uuid.uuid4())
    ahora = datetime.now()
    link_existente.email = user.email
    link_existente.password = get_password_hash(user.password)
    link_existente.phone = user.phone
    link_existente.activation_token = activation_token
    link_existente.status = user.status
    link_existente.updated_at = ahora
    link_existente.updated_by = actor
    usuario.updated_at = ahora
    usuario.updated_by = actor

    try:
        user_repository.update(usuario)
        user_tenant_repository.update(link_existente)
    except IntegrityError as exc:
        logger.exception(
            "Error de integridad al reactivar usuario",
            extra={
                "dni": usuario.dni,
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
                "dni": usuario.dni,
                "tenant_id": tenant_id,
                "user_tenant_id": link_existente.id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al reactivar usuario",
        ) from exc

    return link_existente


def create_global_user(
    user: UserCreate,
    tenant_id: int,
    actor: str,
    user_repository: UserRepository,
) -> UserDB:
    ahora = datetime.now()
    nuevo_usuario = UserDB(
        dni=user.dni,
        name=user.name,
        created_at=ahora,
        created_by=actor,
    )

    try:
        return user_repository.add(nuevo_usuario)
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
    tenant = tenant_repository.get_by_id(tenant_id=tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )

    tenant_slug = tenant.slug
    tenant_name = tenant.name
    actor = _actor_dni(current_user)
    existente = user_repository.get_by_dni(user.dni)
    es_reactivacion = False

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
            nuevo_user_tenant = create_tenant_link(
                user,
                nuevo_usuario,
                tenant_id,
                actor,
                user_tenant_repository,
            )
        elif link_existente.status == 3:
            es_reactivacion = True
            nuevo_user_tenant = reactivate_user(
                user,
                nuevo_usuario,
                link_existente,
                tenant_id,
                actor,
                user_repository,
                user_tenant_repository,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El usuario ya pertenece al tenant",
            )
    else:
        nuevo_usuario = create_global_user(
            user,
            tenant_id,
            actor,
            user_repository,
        )
        nuevo_user_tenant = create_tenant_link(
            user,
            nuevo_usuario,
            tenant_id,
            actor,
            user_tenant_repository,
        )

    logger.info(
        "Usuario asociado correctamente al tenant",
        extra={
            "user_id": nuevo_usuario.id,
            "dni": nuevo_usuario.dni,
            "tenant_id": tenant_id,
            "user_tenant_id": nuevo_user_tenant.id,
        },
    )

    send_user_notifications(
        user=nuevo_usuario,
        user_tenant=nuevo_user_tenant,
        tenant_name=tenant_name,
        tenant_slug=tenant_slug,
        es_reactivacion=es_reactivacion,
    )

    return _user_payload(nuevo_usuario, nuevo_user_tenant)
