from sqlalchemy.orm import Session

from ..services.user_tenant_service import (
    list_user_tenants,
)


# ============================================================
# LISTAR TENANT DE UN USUARIO DENTRO DEL CONTEXTO ACTUAL
# ============================================================

def listar_tenants_usuario(
    user_id: int,
    current_tenant_id: int,
    db: Session,
):

    return list_user_tenants(
        user_id=user_id,
        current_tenant_id=current_tenant_id,
        db=db,
    )