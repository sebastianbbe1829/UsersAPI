from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import PermissionDB
from ..repositories.permission_repository import PermissionRepository
from ..schemas import PermissionCreate


# ============================================================
# LISTAR PERMISOS
# ============================================================

def list_permission(
    db: Session,
):

    repo = PermissionRepository(db)

    permissions = repo.get_all_by_permission()

    logger.debug(
        "Listando permisos"
    )

    return permissions


# ============================================================
# OBTENER PERMISO POR CÓDIGO
# ============================================================

def get_permission(
    code: str,
    db: Session,
):

    repo = PermissionRepository(db)

    permission = repo.get_by_code(code)

    if not permission:

        logger.warning(
            "Permiso no encontrado",
            extra={
                "code": code,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permiso no encontrado",
        )

    logger.debug(
        "Permiso obtenido",
        extra={
            "code": permission.code,
        },
    )

    return permission


# ============================================================
# CREAR PERMISO
# ============================================================

def create_permission(
    datos: PermissionCreate,
    current_user,
    db: Session,
):

    repo = PermissionRepository(db)

    # ========================================================
    # NORMALIZAR DATOS
    # ========================================================

    code = datos.code.strip().upper()
    name = datos.name.strip()

    description = (
        datos.description.strip()
        if datos.description
        else None
    )

    # ========================================================
    # VALIDAR CÓDIGO
    # ========================================================

    if not code:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código del permiso es obligatorio.",
        )

    if not name:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre del permiso es obligatorio.",
        )

    # ========================================================
    # VALIDAR EXISTENCIA
    #
    # Incluye permisos inactivos.
    # ========================================================

    existente = repo.get_by_code_any_status(
        code
    )

    if existente:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"El permiso '{code}' ya existe."
            ),
        )

    # ========================================================
    # CREAR PERMISO
    # ========================================================

    permission = PermissionDB(
        code=code,
        name=name,
        description=description,
        status=1,
        created_by=current_user.user.dni,
    )

    try:

        permission = repo.create(
            permission
        )

        db.commit()

        db.refresh(permission)

    except IntegrityError as exc:

        db.rollback()

        logger.error(
            "Error de integridad creando permiso '%s': %s",
            code,
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"El permiso '{code}' ya existe."
            ),
        ) from exc

    except Exception as exc:

        db.rollback()

        logger.error(
            "Error creando permiso '%s': %s",
            code,
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible crear el permiso.",
        ) from exc

    logger.info(
        "Permiso creado code=%s usuario=%s",
        permission.code,
        current_user.user.dni,
    )

    return permission