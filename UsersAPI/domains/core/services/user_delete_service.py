from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from UsersAPI.domains.cash.models import UserCashAssignmentDB

from ..logging_config import logger
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
        db.execute(
            update(UserCashAssignmentDB)
            .where(
                UserCashAssignmentDB.tenant_id == tenant_id,
                UserCashAssignmentDB.user_tenant_id == link.id,
                UserCashAssignmentDB.status == 1,
            )
            .values(
                status=0,
                unassigned_at=datetime.now(),
                unassigned_by="user deletion",
            )
        )
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
