import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from ..logging_config import logger
from ..models import UserDB, UserTenantDB
from ..repositories.user_repository import UserRepository
from ..repositories.user_tenant_repository import UserTenantRepository
from ..schemas import UserCreate
from .auth_service import get_password_hash


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
