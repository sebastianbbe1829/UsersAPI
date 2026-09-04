from sqlalchemy.orm import Session

from ..logging_config import logger
from ..repositories.user_repository import UserRepository
from ..repositories.user_tenant_repository import UserTenantRepository
from .user_service_helpers import _get_user_entity, _tenant_link, _user_payload


def list_users(
    db: Session,
    tenant_id: int,
    status_filter: int | None = None,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    users = user_repository.get_all_by_tenant(tenant_id, status_filter)
    logger.debug(
        "Usuarios consultados por tenant",
        extra={"tenant_id": tenant_id, "cantidad": len(users)},
    )
    resultado = []
    for user in users:
        link = _tenant_link(user, tenant_id, user_tenant_repository)
        resultado.append(_user_payload(user, link))
    return resultado


def get_user(
    dni: str,
    db: Session,
    tenant_id: int,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    usuario = _get_user_entity(dni, tenant_id, user_repository)
    link = _tenant_link(usuario, tenant_id, user_tenant_repository)
    return _user_payload(usuario, link)
