from datetime import datetime
from uuid import uuid4

from UsersAPI.controllers.auth_controller import create_access_token, pwd_context
from UsersAPI.database import BootstrapSessionLocal, set_rls_tenant
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
    """Crea un contexto multi-tenant respetando el aislamiento RLS."""
    suffix = uuid4().hex[:10]
    now = datetime.now()

    bootstrap_db = BootstrapSessionLocal()
    try:
        tenant = TenantDB(
            name=f"Tenant {suffix}",
            slug=f"tenant-{suffix}",
            status=1,
            created_at=now,
            created_by="test",
        )
        bootstrap_db.add(tenant)
        bootstrap_db.flush()
        bootstrap_db.commit()
        tenant_id = tenant.id
        tenant_slug = tenant.slug
    except Exception:
        bootstrap_db.rollback()
        raise
    finally:
        bootstrap_db.close()

    set_rls_tenant(db, tenant_id)

    tenant = db.get(TenantDB, tenant_id)
    if tenant is None:
        raise RuntimeError("No fue posible recuperar el tenant de prueba")

    user = UserDB(
        dni=f"{uuid4().int % 100000000:08d}",
        name=name,
        created_at=now,
        created_by="test",
    )

    db.add(user)
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

    user_tenant_role = UserTenantRoleDB(
        user_tenant_id=user_tenant.id,
        role_id=role.id,
    )
    db.add(user_tenant_role)
    db.flush()

    # Cargar la relación mientras el contexto RLS todavía corresponde a este
    # tenant. No expirarla después: el mismo db_session puede crear otro tenant
    # y cambiar el contexto RLS antes de que el caller use este objeto.
    db.refresh(user_tenant)
    list(user_tenant.roles)

    token = create_access_token(
        {
            "sub": user.dni,
            "tenant_id": tenant.id,
            "tenant_slug": tenant_slug,
            "user_tenant_id": user_tenant.id,
        }
    )

    db.info.setdefault("bootstrap_tenant_ids", []).append(tenant_id)

    return user, tenant, user_tenant, token
