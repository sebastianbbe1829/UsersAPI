from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_bootstrap_db, get_db, set_rls_tenant
from ..models import TenantDB
from ..repositories.tenant_config_repository import TenantConfigRepository
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
    bootstrap_db: Session = Depends(get_bootstrap_db),
):
    slug_normalizado = tenant_slug.strip().lower()

    # La resolución inicial por slug debe hacerse fuera de RLS,
    # porque todavía no conocemos el tenant_id necesario para
    # establecer el contexto RLS de la conexión normal.
    tenant = (
        bootstrap_db.query(TenantDB)
        .filter(
            func.lower(func.trim(TenantDB.slug)) == slug_normalizado,
            TenantDB.status == 1,
        )
        .first()
    )

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró un tenant activo con el slug solicitado.",
        )

    # A partir de este punto, la configuración se consulta utilizando
    # la conexión normal y con el contexto RLS del tenant establecido.
    set_rls_tenant(db, tenant.id)

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
