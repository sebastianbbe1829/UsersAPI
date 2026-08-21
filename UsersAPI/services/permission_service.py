from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from ..logging_config import logger
from ..repositories.permission_repository import PermissionRepository


def list_permission(
    db: Session,
):
    repo = PermissionRepository(db)
    permissions = repo.get_all_by_permission()
    logger.debug(
        "Listando permisos"
    )
    return permissions

def get_permission(
    code: str,
    db: Session,
):
    repo = PermissionRepository(db)
    permission = repo.get_by_code(code)
    if not permission:
        logger.warning(
            "Permiso no encontrado",extra={
                        "code": code,
                    }
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permiso no encontrado",
        )

    logger.debug(
        "Permiso obtenido",
        extra={
            "code": permission,
        },
    )
    return permission