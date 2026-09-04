from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import GlobalUserDB, TenantConfigDB, UserTenantDB
from ..repositories.tenant_config_repository import TenantConfigRepository
from ..schemas import TenantConfigUpdate

DEFAULT_PRIMARY_COLOR = "#0D6EFD"
DEFAULT_SECONDARY_COLOR = "#6C757D"
DEFAULT_MAX_LOGIN_ATTEMPTS = 0


def _actor(current_user: UserTenantDB | GlobalUserDB) -> str:
    return current_user.email


def get_or_create_tenant_config(
    tenant_id: int,
    tenant_name: str,
    db: Session,
    current_user: UserTenantDB | GlobalUserDB,
):
    repo = TenantConfigRepository(db)
    config = repo.get_by_tenant_id(tenant_id)
    if config is not None:
        return config

    config = TenantConfigDB(
        tenant_id=tenant_id,
        app_title=tenant_name,
        logo_url=None,
        primary_color=DEFAULT_PRIMARY_COLOR,
        secondary_color=DEFAULT_SECONDARY_COLOR,
        max_login_attempts=DEFAULT_MAX_LOGIN_ATTEMPTS,
        created_at=datetime.now(),
        created_by=_actor(current_user),
    )

    try:
        return repo.add(config)
    except IntegrityError:
        db.rollback()
        config = repo.get_by_tenant_id(tenant_id)
        if config is not None:
            return config
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No fue posible crear la configuración del tenant",
        ) from None


def read_tenant_config(
    tenant_id: int,
    tenant_name: str,
    db: Session,
    current_user: UserTenantDB | GlobalUserDB,
):
    return get_or_create_tenant_config(tenant_id, tenant_name, db, current_user)


def update_tenant_config(
    tenant_id: int,
    tenant_name: str,
    datos: TenantConfigUpdate,
    db: Session,
    current_user: UserTenantDB | GlobalUserDB,
):
    config = get_or_create_tenant_config(tenant_id, tenant_name, db, current_user)
    values = datos.model_dump(exclude_unset=True)
    for field, value in values.items():
        setattr(config, field, value)
    config.updated_at = datetime.now()
    config.updated_by = _actor(current_user)
    return TenantConfigRepository(db).update(config)
