from sqlalchemy.orm import Session

from ..models import TenantDB, UserTenantDB
from ..schemas import TenantConfigUpdate
from ..services.tenant_config_service import (
    read_tenant_config,
    update_tenant_config,
)


def _to_response(tenant: TenantDB, config):
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


def obtener_config_tenant(
    tenant: TenantDB,
    db: Session,
    current_user: UserTenantDB,
):
    config = read_tenant_config(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        db=db,
        current_user=current_user,
    )
    return _to_response(tenant, config)


def actualizar_config_tenant(
    tenant: TenantDB,
    datos: TenantConfigUpdate,
    db: Session,
    current_user: UserTenantDB,
):
    config = update_tenant_config(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        datos=datos,
        db=db,
        current_user=current_user,
    )
    return _to_response(tenant, config)
