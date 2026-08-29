from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..repositories.tenant_config_repository import TenantConfigRepository
from ..repositories.tenant_repository import TenantRepository
from ..schemas import TenantConfigRead


tenant_config_public_routes = APIRouter(
    prefix="/tenant-config/public",
    tags=["Configuración UI"],
)


@tenant_config_public_routes.get(
    "/{tenant_slug}",
    response_model=TenantConfigRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener configuración visual pública de un tenant",
)
async def obtener_config_tenant_publica_route(
    tenant_slug: str,
    db: Session = Depends(get_db),
):
    tenant_repository = TenantRepository(db)
    tenant = tenant_repository.get_by_slug(tenant_slug)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el tenant solicitado.",
        )

    config_repository = TenantConfigRepository(db)
    config = config_repository.get_by_tenant_id(tenant.id)

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la configuración visual del tenant.",
        )

    return {
        "tenant_id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "app_title": config.app_title,
        "logo_url": config.logo_url,
        "primary_color": config.primary_color,
        "secondary_color": config.secondary_color,
        "updated_at": config.updated_at,
    }
