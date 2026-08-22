from datetime import datetime
from uuid import uuid4

from UsersAPI.controllers.auth_controller import create_access_token, pwd_context
from UsersAPI.models import (
    PermissionDB,
    RoleDB,
    RolePermissionDB,
    TenantDB,
    UserDB,
    UserTenantDB,
    UserTenantRoleDB,
)


TEST_PERMISSIONS = (
    "AUTHENTICATE",
    "USER_CREATE",
    "USER_READ",
    "USER_UPDATE",
    "USER_DELETE",
    "USER_EXPORT",
    "TENANT_CREATE",
    "TENANT_READ",
    "TENANT_UPDATE",
    "TENANT_DELETE",
)


def create_user_context(db, *, password="oldpass", name="Test User"):
    """Crea un contexto completo y aislado para pruebas multi-tenant."""
    suffix = uuid4().hex[:10]
    now = datetime.now()

    tenant = TenantDB(
        name=f"Tenant {suffix}",
        slug=f"tenant-{suffix}",
        status=1,
        created_at=now,
        created_by="test",
    )

    user = UserDB(
        dni=f"{uuid4().int % 100000000:08d}",
        name=name,
        created_at=now,
        created_by="test",
    )

    db.add_all([tenant, user])
    db.flush()

    user_tenant = UserTenantDB(
        user_id=user.id,
        tenant_id=tenant.id,
        email=f"{suffix}@example.com",
        password=pwd_context.hash(password),
        phone="3000000000",
        status=1,
        created_at=now,
        created_by="test",
    )
    db.add(user_tenant)
    db.flush()

    role = RoleDB(
        tenant_id=tenant.id,
        code=f"TEST-{suffix}",
        name="Test role",
        status=1,
        created_at=now,
        created_by="test",
    )
    db.add(role)
    db.flush()

    for code in TEST_PERMISSIONS:
        permission = (
            db.query(PermissionDB)
            .filter(PermissionDB.code == code)
            .first()
        )

        if permission is None:
            permission = PermissionDB(
                code=code,
                name=code,
                status=1,
                created_at=now,
                created_by="test",
            )
            db.add(permission)
            db.flush()

        db.add(
            RolePermissionDB(
                role_id=role.id,
                permission_id=permission.id,
            )
        )

    db.add(
        UserTenantRoleDB(
            user_tenant_id=user_tenant.id,
            role_id=role.id,
        )
    )

    db.commit()
    db.refresh(user)
    db.refresh(user_tenant)

    token = create_access_token(
        {
            "sub": user.dni,
            "tenant_id": tenant.id,
            "tenant_slug": tenant.slug,
            "user_tenant_id": user_tenant.id,
        }
    )

    return user, tenant, user_tenant, token
