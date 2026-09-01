from datetime import datetime
from uuid import uuid4

from UsersAPI.database import BootstrapSessionLocal, set_rls_tenant
from UsersAPI.models import TenantDB, UserDB, UserTenantDB
from UsersAPI.controllers.auth_controller import pwd_context


def create_activation_context(db, *, password="oldpass", status=0):
    suffix = uuid4().hex[:10]
    now = datetime.now()
    activation_token = str(uuid4())

    bootstrap_db = BootstrapSessionLocal()
    try:
        tenant = TenantDB(
            name=f"Activation Tenant {suffix}",
            slug=f"activation-{suffix}",
            status=1,
            created_at=now,
            created_by="test",
        )
        bootstrap_db.add(tenant)
        bootstrap_db.flush()
        bootstrap_db.commit()
        tenant_id = tenant.id
    except Exception:
        bootstrap_db.rollback()
        raise
    finally:
        bootstrap_db.close()

    set_rls_tenant(db, tenant_id)
    tenant = db.get(TenantDB, tenant_id)

    user = UserDB(
        dni=f"{uuid4().int % 100000000:08d}",
        name="Activation User",
        created_at=now,
        created_by="test",
    )
    db.add(user)
    db.flush()

    user_tenant = UserTenantDB(
        user_id=user.id,
        tenant_id=tenant.id,
        email=f"activation-{suffix}@example.com",
        password=pwd_context.hash(password),
        phone="3000000000",
        activation_token=activation_token,
        status=status,
        created_at=now,
        created_by="test",
    )
    db.add(user_tenant)
    db.flush()
    db.refresh(user_tenant)

    db.info.setdefault("bootstrap_tenant_ids", []).append(tenant_id)

    return user, tenant, user_tenant, activation_token
