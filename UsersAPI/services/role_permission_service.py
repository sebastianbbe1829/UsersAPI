from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import PermissionDB, RoleDB, RolePermissionDB
from ..repositories.role_permission_repository import (
    RolePermissionRepository,
)


def assign_permission_to_role(
    role_id: int,
    permission_id: int,
    tenant_id: int,
    db: Session,
    current_user=None,
) -> RolePermissionDB:

    repo = RolePermissionRepository(db)

    # ============================================================
    # VALIDAR QUE EL ROL EXISTA EN EL TENANT
    # ============================================================

    role = (
        db.query(RoleDB)
        .filter(
            RoleDB.id == role_id,
            RoleDB.tenant_id == tenant_id,
            RoleDB.status == 1,
        )
        .first()
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El rol no existe en el tenant seleccionado",
        )

    # ============================================================
    # VALIDAR QUE EL PERMISO EXISTA
    # ============================================================

    permission = (
        db.query(PermissionDB)
        .filter(
            PermissionDB.id == permission_id,
            PermissionDB.status == 1,
        )
        .first()
    )

    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El permiso no existe o está inactivo",
        )

    # ============================================================
    # VALIDAR QUE NO EXISTA YA LA RELACIÓN
    # ============================================================

    existente = repo.get_by_role_permission(
        role_id=role_id,
        permission_id=permission_id,
    )

    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El permiso ya está asignado al rol",
        )

    # ============================================================
    # CREAR RELACIÓN
    # ============================================================

    nueva_relacion = RolePermissionDB(
        role_id=role_id,
        permission_id=permission_id,
    )

    try:

        creado = repo.add(nueva_relacion)

        logger.info(
            "Permiso asignado a rol",
            extra={
                "role_id": role_id,
                "role_code": role.code,
                "permission_id": permission_id,
                "permission_code": permission.code,
                "tenant_id": tenant_id,
                "created_by": (
                    current_user.email
                    if current_user
                    else "bootstrap"
                ),
            },
        )

        return creado

    except IntegrityError:

        db.rollback()

        logger.warning(
            "Error al asignar permiso al rol",
            extra={
                "role_id": role_id,
                "permission_id": permission_id,
                "tenant_id": tenant_id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El permiso ya está asignado al rol",
        ) from None

    except Exception as exc:

        db.rollback()

        logger.error(
            "Error inesperado al asignar permiso al rol: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al asignar permiso al rol",
        ) from exc


def list_role_permissions(
    role_id: int,
    tenant_id: int,
    db: Session,
):

    role = (
        db.query(RoleDB)
        .filter(
            RoleDB.id == role_id,
            RoleDB.tenant_id == tenant_id,
            RoleDB.status == 1,
        )
        .first()
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El rol no existe en el tenant seleccionado",
        )

    repo = RolePermissionRepository(db)

    return repo.get_permissions_by_role(
        role_id=role_id,
    )


def remove_permission_from_role(
    role_permission_id: int,
    tenant_id: int,
    db: Session,
):

    repo = RolePermissionRepository(db)

    role_permission = repo.get_by_id(
        role_permission_id=role_permission_id,
    )

    if role_permission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La relación rol-permiso no existe",
        )

    role = (
        db.query(RoleDB)
        .filter(
            RoleDB.id == role_permission.role_id,
            RoleDB.tenant_id == tenant_id,
        )
        .first()
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El rol no pertenece al tenant seleccionado",
        )

    repo.delete(role_permission)

    logger.info(
        "Permiso eliminado del rol",
        extra={
            "role_permission_id": role_permission_id,
            "role_id": role_permission.role_id,
            "permission_id": role_permission.permission_id,
            "tenant_id": tenant_id,
        },
    )

    return {
        "id": role_permission.id,
        "role_id": role_permission.role_id,
        "permission_id": role_permission.permission_id,
        "message": "Permiso eliminado del rol correctamente",
    }