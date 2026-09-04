from sqlalchemy.orm import Session

from ..models import (
    UserTenantDB,
    UserTenantRoleDB,
    RoleDB,
    RolePermissionDB,
    PermissionDB,
)


def user_can_authenticate(
    user_tenant: UserTenantDB,
    db: Session,
) -> bool:
    permission = (
        db.query(PermissionDB)
        .join(RolePermissionDB, RolePermissionDB.permission_id == PermissionDB.id)
        .join(RoleDB, RoleDB.id == RolePermissionDB.role_id)
        .join(UserTenantRoleDB, UserTenantRoleDB.role_id == RoleDB.id)
        .filter(
            UserTenantRoleDB.user_tenant_id == user_tenant.id,
            RoleDB.tenant_id == user_tenant.tenant_id,
            RoleDB.status == 1,
            PermissionDB.status == 1,
            PermissionDB.code == "AUTHENTICATE",
        )
        .first()
    )

    return permission is not None


def get_user_permissions(
    user_tenant: UserTenantDB,
    db: Session,
) -> list[str]:
    permissions = (
        db.query(PermissionDB.code)
        .join(RolePermissionDB, RolePermissionDB.permission_id == PermissionDB.id)
        .join(RoleDB, RoleDB.id == RolePermissionDB.role_id)
        .join(UserTenantRoleDB, UserTenantRoleDB.role_id == RoleDB.id)
        .filter(
            UserTenantRoleDB.user_tenant_id == user_tenant.id,
            RoleDB.tenant_id == user_tenant.tenant_id,
            RoleDB.status == 1,
            PermissionDB.status == 1,
        )
        .distinct()
        .order_by(PermissionDB.code)
        .all()
    )

    return [code for (code,) in permissions]
