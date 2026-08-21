from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import RoleDB
from ..repositories.role_repository import RoleRepository


def create_role(
    tenant_id: int,
    code: str,
    name: str,
    description: str | None,
    db: Session,
    current_user=None,
) -> RoleDB:

    repo = RoleRepository(db)

    code = code.strip().lower()
    name = name.strip()

    # Validar código dentro del tenant
    existente_code = repo.get_by_code(
        code=code,
        tenant_id=tenant_id,
    )

    if existente_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un rol con ese código en el tenant",
        )

    # Validar nombre dentro del tenant
    existente_name = repo.get_by_name(
        name=name,
        tenant_id=tenant_id,
    )

    if existente_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un rol con ese nombre en el tenant",
        )

    nuevo_role = RoleDB(
        tenant_id=tenant_id,
        code=code,
        name=name,
        description=description,
        status=1,
        created_by=(
            current_user.email
            if current_user
            else "bootstrap"
        ),
        created_at=datetime.now(),
    )

    try:

        creado = repo.add(nuevo_role)

        logger.info(
            "Rol creado",
            extra={
                "role_id": creado.id,
                "tenant_id": tenant_id,
                "role_code": creado.code,
                "role_name": creado.name,
            },
        )

        return creado

    except IntegrityError:

        db.rollback()

        logger.warning(
            "Error al crear rol",
            extra={
                "tenant_id": tenant_id,
                "role_code": code,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol ya existe en el tenant",
        ) from None

    except Exception as exc:

        db.rollback()

        logger.error(
            "Error inesperado al crear rol: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear rol",
        ) from exc


def list_roles(
    tenant_id: int,
    db: Session,
    status_filter: int | None = None,
):

    repo = RoleRepository(db)

    roles = repo.get_all_by_tenant(
        tenant_id=tenant_id,
        status_filter=status_filter,
    )

    logger.debug(
        "Listando roles del tenant",
        extra={
            "tenant_id": tenant_id,
            "count": len(roles),
            "status_filter": status_filter,
        },
    )

    return roles


def get_role(
    role_id: int,
    tenant_id: int,
    db: Session,
):

    repo = RoleRepository(db)

    role = repo.get_by_id(
        role_id=role_id,
        tenant_id=tenant_id,
    )

    if not role:

        logger.warning(
            "Rol no encontrado",
            extra={
                "role_id": role_id,
                "tenant_id": tenant_id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado",
        )

    return role


def update_role(
    role_id: int,
    tenant_id: int,
    code: str | None,
    name: str | None,
    description: str | None,
    status: int | None,
    db: Session,
    current_user=None,
):

    repo = RoleRepository(db)

    role = repo.get_by_id(
        role_id=role_id,
        tenant_id=tenant_id,
    )

    if not role:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado",
        )

    # Actualizar código
    if code is not None:

        code = code.strip().lower()

        otro_role = repo.get_by_code(
            code=code,
            tenant_id=tenant_id,
        )

        if otro_role and otro_role.id != role.id:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro rol con ese código",
            )

        role.code = code

    if status is not None:
        if status not in (0, 1):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El estado del rol debe ser 0 o 1",
            )

        role.status = status

    # Actualizar nombre
    if name is not None:

        name = name.strip()

        otro_role = repo.get_by_name(
            name=name,
            tenant_id=tenant_id,
        )

        if otro_role and otro_role.id != role.id:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro rol con ese nombre",
            )

        role.name = name

    if description is not None:
        role.description = description

    role.updated_by = (
        current_user.email
        if current_user
        else "bootstrap"
    )

    role.updated_at = datetime.now()

    try:

        actualizado = repo.update(role)

        logger.info(
            "Rol actualizado",
            extra={
                "role_id": actualizado.id,
                "tenant_id": tenant_id,
            },
        )

        return actualizado

    except IntegrityError:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fue posible actualizar el rol",
        ) from None


def delete_role(
    role_id: int,
    tenant_id: int,
    db: Session,
):

    repo = RoleRepository(db)

    role = repo.get_by_id(
        role_id=role_id,
        tenant_id=tenant_id,
    )

    if not role:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado",
        )

    repo.delete(role)

    logger.info(
        "Rol eliminado (soft delete)",
        extra={
            "role_id": role.id,
            "tenant_id": tenant_id,
            "role_name": role.name,
        },
    )

    return {
        "id": role.id,
        "tenant_id": role.tenant_id,
        "code": role.code,
        "name": role.name,
        "status": role.status,
        "message": "Rol eliminado correctamente",
    }