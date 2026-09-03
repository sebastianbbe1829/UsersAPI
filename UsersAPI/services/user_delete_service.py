from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import GlobalUserDB, UserTenantDB
from ..repositories.user_repository import UserRepository
from ..repositories.user_tenant_repository import UserTenantRepository
from .user_service_helpers import _get_user_entity, _tenant_link, _user_payload


def delete_user(
    dni: str,
    db: Session,
    tenant_id: int,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    usuario = _get_user_entity(dni, tenant_id, user_repository)
    link = _tenant_link(usuario, tenant_id, user_tenant_repository)
    try:
        user_tenant_repository.delete(link)
    except Exception as exc:
        logger.exception(
            "Error al eliminar usuario",
            extra={"dni": dni, "tenant_id": tenant_id},
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
