from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import TenantDB, UserDB
from ..repositories.tenant_repository import TenantRepository


def create_tenant(
    name: str,
    slug: str,
    db: Session,
    current_user: UserDB | None = None,
) -> TenantDB:

    repo = TenantRepository(db)

    # Normalizamos los valores
    name = name.strip()
    slug = slug.strip().lower()

    # Validar nombre
    existente_nombre = repo.get_by_name(name)

    if existente_nombre:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un tenant con ese nombre",
        )

    # Validar slug
    existente_slug = repo.get_by_slug(slug)

    if existente_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El slug ya está registrado",
        )

    nuevo_tenant = TenantDB(
        name=name,
        slug=slug,
        status=1,
        created_by=(
            current_user.email
            if current_user
            else "bootstrap"
        ),
        created_at=datetime.now(),
    )

    try:
        creado = repo.add(nuevo_tenant)

        logger.info(
            "Tenant creado",
            extra={
                "tenant_id": creado.id,
                "tenant_name": creado.name,
                "slug": creado.slug,
            },
        )

        return creado

    except IntegrityError:
        db.rollback()

        logger.warning(
            "Error al crear tenant: nombre o slug duplicado",
            extra={
                "tenant_name": name,
                "slug": slug,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tenant ya existe o el slug ya está registrado",
        ) from None

    except Exception as exc:
        db.rollback()

        logger.error(
            "Error inesperado al crear tenant: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear tenant",
        ) from exc


def list_tenants(
    db: Session,
    status_filter: int | None = None,
):

    repo = TenantRepository(db)

    tenants = repo.get_all(status_filter)

    logger.debug(
        "Listando tenants",
        extra={
            "count": len(tenants),
            "status_filter": status_filter,
        },
    )

    return tenants


def get_tenant(
    tenant_id: int,
    db: Session,
):

    repo = TenantRepository(db)

    tenant = repo.get_by_id(tenant_id)

    if not tenant:
        logger.warning(
            "Tenant no encontrado",
            extra={
                "tenant_id": tenant_id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )

    logger.debug(
        "Tenant obtenido",
        extra={
            "tenant_id": tenant_id,
        },
    )

    return tenant


def update_tenant(
    tenant_id: int,
    name: str | None,
    slug: str | None,
    db: Session,
    current_user: UserDB | None = None,
):

    repo = TenantRepository(db)

    tenant = repo.get_by_id(tenant_id)

    if not tenant:
        logger.warning(
            "Tenant no encontrado al actualizar",
            extra={
                "tenant_id": tenant_id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )

    # Actualizar nombre
    if name is not None:

        name = name.strip()

        otro_tenant = repo.get_by_name(name)

        if otro_tenant and otro_tenant.id != tenant.id:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro tenant con ese nombre",
            )

        tenant.name = name

    # Actualizar slug
    if slug is not None:

        slug = slug.strip().lower()

        otro_tenant = repo.get_by_slug(slug)

        if otro_tenant and otro_tenant.id != tenant.id:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El slug ya está registrado",
            )

        tenant.slug = slug

    tenant.updated_by = (
        current_user.email
        if current_user
        else "bootstrap"
    )

    tenant.updated_at = datetime.now()

    try:

        actualizado = repo.update(tenant)

        logger.info(
            "Tenant actualizado",
            extra={
                "tenant_id": actualizado.id,
                "tenant_name": actualizado.name,
                "slug": actualizado.slug,
            },
        )

        return actualizado

    except IntegrityError:

        db.rollback()

        logger.warning(
            "Error al actualizar tenant",
            extra={
                "tenant_id": tenant_id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fue posible actualizar el tenant",
        ) from None


def delete_tenant(
    tenant_id: int,
    db: Session,
):

    repo = TenantRepository(db)

    tenant = repo.get_by_id(tenant_id)

    if not tenant:

        logger.warning(
            "Tenant no encontrado al eliminar",
            extra={
                "tenant_id": tenant_id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )

    repo.delete(tenant)

    logger.info(
        "Tenant eliminado (soft delete)",
        extra={
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "status": tenant.status,
        },
    )

    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "status": tenant.status,
        "message": "Tenant eliminado correctamente",
    }

def list_my_tenants(
    db: Session,
    current_user: UserDB,
):
    repo = TenantRepository(db)

    user_id = current_user.id

    tenants = repo.get_by_user_id(
         user_id=user_id,
         status_filter=1,
    )

    logger.debug(
        "Listando tenants del usuario",
        extra={
            "user_id": user_id,
            "count": len(tenants),
        },
    )

    return tenants