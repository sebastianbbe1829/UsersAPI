from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    PermissionDB,
    UserTenantDB,
)
from .dependencies import get_current_tenant


def require_permission(permission_code: str):

    def permission_checker(
        user_tenant: UserTenantDB = Depends(
            get_current_tenant
        ),
        db: Session = Depends(get_db),
    ):

        permission = (
            db.query(PermissionDB)
            .filter(
                PermissionDB.code == permission_code,
                PermissionDB.status == 1,
            )
            .first()
        )

        if permission is None:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"El permiso '{permission_code}' no existe"
                ),
            )

        has_permission = any(
            permission.code
            == role_permission.permission.code

            for user_tenant_role
            in user_tenant.roles

            for role_permission
            in user_tenant_role.role.permissions

            if role_permission.permission.status == 1
        )

        if not has_permission:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "No tienes permisos para "
                    "realizar esta operación"
                ),
            )

        return user_tenant

    return permission_checker


# ============================================================
# REQUERIR ROL GLOBAL
# ============================================================

def require_global_role(
    role_code: str,
):

    def role_checker(
        user_tenant: UserTenantDB = Depends(
            get_current_tenant
        ),
    ):

        has_role = any(
            user_tenant_role.role.code == role_code
            and user_tenant_role.role.tenant_id is None
            and user_tenant_role.role.status == 1

            for user_tenant_role
            in user_tenant.roles
        )

        if not has_role:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "No tienes permisos globales para "
                    "realizar esta operación"
                ),
            )

        return user_tenant

    return role_checker