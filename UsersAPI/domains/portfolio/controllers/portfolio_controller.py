from uuid import UUID

from sqlalchemy.orm import Session

from UsersAPI.domains.core.models import UserTenantDB

from ..schemas import CreditLimitUpdate, PaymentCreate
from ..services import (
    get_client_credit,
    list_client_obligations,
    list_obligations,
    list_payments,
    register_payment,
    upsert_client_credit_limit,
)


def client_credit(client_id: UUID, db: Session, tenant_id: int):
    return get_client_credit(client_id, db, tenant_id)


def update_client_credit(
    client_id: UUID,
    data: CreditLimitUpdate,
    db: Session,
    tenant_id: int,
    current_user: UserTenantDB,
):
    return upsert_client_credit_limit(client_id, data, db, tenant_id, current_user)


def obligations(db: Session, tenant_id: int):
    return list_obligations(db, tenant_id)


def client_obligations(client_id: UUID, db: Session, tenant_id: int):
    return list_client_obligations(client_id, db, tenant_id)


def create_payment(
    data: PaymentCreate,
    db: Session,
    tenant_id: int,
    current_user: UserTenantDB,
):
    return register_payment(data, db, tenant_id, current_user)


def payments(db: Session, tenant_id: int, client_id: UUID | None = None):
    return list_payments(db, tenant_id, client_id)
