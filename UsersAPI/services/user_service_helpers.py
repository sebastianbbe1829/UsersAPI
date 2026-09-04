from fastapi import HTTPException, status

from ..models import GlobalUserDB, UserDB, UserTenantDB
from ..repositories.user_repository import UserRepository
from ..repositories.user_tenant_repository import UserTenantRepository


# ============================================================
# UTILIDADES DEL SERVICIO DE USUARIOS
# ============================================================

def _actor_dni(
    current_user: UserTenantDB | GlobalUserDB | None,
) -> str:
    if current_user is None:
        return "bootstrap"

    if isinstance(current_user, GlobalUserDB):
        return current_user.email

    return current_user.user.dni


def _user_payload(
    user: UserDB,
    link: UserTenantDB,
    message: str | None = None,
):
    payload = {
        "dni": user.dni,
        "name": user.name,
        "email": link.email,
        "phone": link.phone,
        "status": link.status,
        "id": user.id,
        "failed_login_attempts": link.failed_login_attempts or 0,
        "locked_at": link.locked_at,
    }

    if message is not None:
        payload["message"] = message

    return payload


def _tenant_link(
    user: UserDB,
    tenant_id: int,
    user_tenant_repository: UserTenantRepository,
) -> UserTenantDB:
    link = user_tenant_repository.get_by_user_and_tenant(
        user.id,
        tenant_id,
    )

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no pertenece al tenant",
        )

    return link


def _get_user_entity(
    dni: str,
    tenant_id: int,
    user_repository: UserRepository,
) -> UserDB:
    usuario = user_repository.get_by_dni_in_tenant(
        dni,
        tenant_id,
    )

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    return usuario
