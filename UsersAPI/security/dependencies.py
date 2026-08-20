from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..controllers.auth_controller import get_current_user
from ..database import get_db
from ..models import UserDB, UserTenantDB


def get_current_tenant(
    x_tenant_id: str | None = Header(
        default=None,
        alias="X-Tenant-ID",
    ),
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserTenantDB:

    # ============================================================
    # VALIDAR QUE EL HEADER EXISTA
    # ============================================================

    if x_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe especificar el tenant mediante el header X-Tenant-ID",
        )

    # ============================================================
    # VALIDAR QUE EL HEADER NO ESTÉ VACÍO
    # ============================================================

    if not x_tenant_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El header X-Tenant-ID no puede estar vacío",
        )

    # ============================================================
    # VALIDAR QUE EL TENANT SEA UN ENTERO
    # ============================================================

    try:
        tenant_id = int(x_tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El header X-Tenant-ID debe ser un número entero",
        )

    # ============================================================
    # VALIDAR PERTENENCIA DEL USUARIO AL TENANT
    # ============================================================

    user_tenant = (
        db.query(UserTenantDB)
        .filter(
            UserTenantDB.user_id == current_user.id,
            UserTenantDB.tenant_id == tenant_id,
            UserTenantDB.status == 1,
        )
        .first()
    )

    if user_tenant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no pertenece al tenant seleccionado",
        )

    return user_tenant