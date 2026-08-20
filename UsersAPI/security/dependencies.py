from typing import cast

from fastapi import Depends, HTTPException, status

from ..controllers.auth_controller import get_current_user
from ..models import UserTenantDB


def get_current_tenant(
    current_user: UserTenantDB = Depends(get_current_user),
) -> UserTenantDB:

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no autenticado",
        )


    user_status = cast(
        int,
        current_user.status,
    )

    if user_status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no está activo en el tenant",
        )


    tenant_status = cast(
        int,
        current_user.tenant.status,
    )

    if tenant_status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El tenant no está activo",
        )


    return current_user