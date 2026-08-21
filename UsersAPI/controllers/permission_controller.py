from sqlalchemy.orm import Session


from ..services.permission_service import (
    list_permission,
    get_permission
)



def listar_permisos(
    db: Session,
):
    return list_permission(
        db=db,
    )


def obtener_permiso(
    code: str,
    db: Session,
):
    return get_permission(
        code=code,
        db=db,
    )


