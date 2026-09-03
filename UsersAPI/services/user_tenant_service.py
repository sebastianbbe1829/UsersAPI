from fastapi import HTTPException, status
from sqlalchemy.orm import Session


from ..repositories.user_repository import UserRepository
from ..repositories.user_tenant_repository import UserTenantRepository

# ============================================================
# LISTAR TENANTS DE UN USUARIO DENTRO DEL CONTEXTO ACTUAL
# ============================================================

def list_user_tenants(
    user_id: int,
    current_tenant_id: int,
    db: Session,
):

    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)

    usuario = user_repository.get_by_id_including_deleted(user_id)

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no existe",
        )

    asociacion = user_tenant_repository.get_by_user_and_tenant(
        user_id=user_id,
        tenant_id=current_tenant_id,
    )

    if asociacion is None:
        return []

    return [asociacion]