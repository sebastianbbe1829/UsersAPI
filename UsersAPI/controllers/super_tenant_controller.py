from sqlalchemy.orm import Session

from ..models import GlobalUserDB
from ..schemas import BootstrapRequest, BootstrapResponse, TenantUpdate
from ..services.super_tenant_service import (
    get_any_tenant,
    list_all_tenants,
    provision_tenant,
    update_any_tenant,
)
from ..services.super_tenant_service import require_super_user
from ..services.super_mfa_service import verify_super_mfa_otp


def listar_tenants_super(db: Session, current_user):
    require_super_user(current_user)
    return list_all_tenants(db)


def obtener_tenant_super(
    tenant_id: int,
    db: Session,
    current_user,
):
    require_super_user(current_user)
    return get_any_tenant(tenant_id, db)


def crear_tenant_super(
    datos: BootstrapRequest,
    otp: str,
    db: Session,
    current_user,
):
    user = require_super_user(current_user)
    verify_super_mfa_otp(user, otp)

    result = provision_tenant(datos, db)

    tenant = result["tenant"]
    user = result["user"]
    user_tenant = result["user_tenant"]
    role = result["role"]

    return BootstrapResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        user_id=user.id,
        user_dni=user.dni,
        user_name=user.name,
        user_tenant_id=user_tenant.id,
        user_email=user_tenant.email,
        role_id=role.id,
        role_code=role.code,
        role_name=role.name,
        message="Bootstrap realizado correctamente.",
    )


def actualizar_tenant_super(
    tenant_id: int,
    datos: TenantUpdate,
    otp: str,
    db: Session,
    current_user,
):
    user: GlobalUserDB = require_super_user(current_user)
    verify_super_mfa_otp(user, otp)
    return update_any_tenant(
        tenant_id=tenant_id,
        datos=datos,
        db=db,
        current_user=user,
    )
