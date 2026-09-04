from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import GlobalUserDB
from ..repositories.tenant_repository import TenantRepository
from ..schemas import BootstrapTenantRequest, TenantUpdate
from .bootstrap_tenant_service import bootstrapTenant


def require_super_user(current_user) -> GlobalUserDB:
    if not isinstance(current_user, GlobalUserDB):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta operación requiere una sesión SUPER.",
        )

    if not current_user.is_active or not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene privilegios SUPER.",
        )

    return current_user


def list_all_tenants(db: Session):
    repo = TenantRepository(db)
    return repo.get_all()


def get_any_tenant(
    tenant_id: int,
    db: Session,
):
    repo = TenantRepository(db)
    tenant = repo.get_by_id(tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado.",
        )

    return tenant


def provision_tenant(
    datos: BootstrapTenantRequest,
    db: Session,
):
    # Reutiliza exactamente la lógica de provisionamiento del bootstrap
    # técnico, pero esta vez dentro de una sesión SUPER autenticada.
    return bootstrapTenant(
        db=db,
        tenant_name=datos.tenant_name,
        tenant_slug=datos.tenant_slug,
        admin_dni=datos.admin_dni,
        admin_name=datos.admin_name,
        admin_email=str(datos.admin_email),
        admin_password=datos.admin_password,
        admin_phone=datos.admin_phone,
    )


def update_any_tenant(
    tenant_id: int,
    datos: TenantUpdate,
    db: Session,
    current_user: GlobalUserDB,
):
    repo = TenantRepository(db)
    tenant = repo.get_by_id(tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado.",
        )

    if datos.name is None and datos.slug is None and datos.status is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe indicar al menos un campo para actualizar.",
        )

    if datos.name is not None:
        name = datos.name.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="El nombre del tenant no puede estar vacío.",
            )

        otro = repo.get_by_name(name)
        if otro is not None and otro.id != tenant.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro tenant con ese nombre.",
            )

        tenant.name = name

    if datos.slug is not None:
        slug = datos.slug.strip().lower()
        if not slug:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="El slug del tenant no puede estar vacío.",
            )

        otro = repo.get_by_slug(slug)
        if otro is not None and otro.id != tenant.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El slug ya está registrado.",
            )

        tenant.slug = slug

    if datos.status is not None:
        tenant.status = datos.status

    tenant.updated_at = datetime.now()
    tenant.updated_by = current_user.email

    try:
        actualizado = repo.update(tenant)

        logger.info(
            "Tenant actualizado por SUPER",
            extra={
                "tenant_id": actualizado.id,
                "tenant_name": actualizado.name,
                "slug": actualizado.slug,
                "super_email": current_user.email,
            },
        )

        return actualizado

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fue posible actualizar el tenant.",
        ) from exc
