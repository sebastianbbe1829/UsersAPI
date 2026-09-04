from sqlalchemy.orm import Session

from ..schemas import PermissionCreate

from ..services.permission_service import (
    list_permission,
    get_permission,
    create_permission,
)


# ============================================================
# LISTAR PERMISOS
# ============================================================

def listar_permisos(
    db: Session,
):

    return list_permission(
        db=db,
    )


# ============================================================
# OBTENER PERMISO
# ============================================================

def obtener_permiso(
    code: str,
    db: Session,
):

    return get_permission(
        code=code,
        db=db,
    )


# ============================================================
# CREAR PERMISO
# ============================================================

def crear_permiso(
    datos: PermissionCreate,
    current_user,
    db: Session,
):

    return create_permission(
        datos=datos,
        current_user=current_user,
        db=db,
    )