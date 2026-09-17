from fastapi import HTTPException, status

from ..domains.core.models import GlobalUserDB


def require_super_user(current_user) -> GlobalUserDB:
    """Valida que el actor sea un usuario SUPER activo."""
    if not isinstance(current_user, GlobalUserDB):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta operación requiere una sesión SUPER.",
        )

    if not current_user.is_active or not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene privilegios SUPER.",
        )

    return current_user
