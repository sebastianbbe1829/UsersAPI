from datetime import date
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from UsersAPI.domains.cash.services.cash_dependencies import require_operational_cash_context
from UsersAPI.domains.core.controllers import get_current_user
from UsersAPI.domains.core.database import get_db
from UsersAPI.domains.core.models import UserTenantDB
from UsersAPI.security.dependencies import get_current_tenant
from UsersAPI.security.permissions import require_permission

from ..controllers import (
    annul_payment_route,
    client_credit,
    client_obligations,
    create_payment,
    obligations,
    payments,
    update_client_credit,
)
from ..schemas import (
    CreditLimitRead,
    CreditLimitUpdate,
    ObligationRead,
    PaymentCreate,
    PaymentRead,
)

portfolio_routes = APIRouter(prefix="/portfolio", tags=["Cartera"])


@portfolio_routes.get(
    "/clients/{client_id}/credit-limit",
    response_model=CreditLimitRead,
    dependencies=[Depends(require_permission("PORTFOLIO_READ"))],
)
async def get_client_credit_route(
    client_id: UUID,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return client_credit(client_id, db, cast(int, user_tenant.tenant_id))


@portfolio_routes.put(
    "/clients/{client_id}/credit-limit",
    response_model=CreditLimitRead,
    dependencies=[Depends(require_permission("PORTFOLIO_CREDIT_UPDATE"))],
)
async def update_client_credit_route(
    client_id: UUID,
    data: CreditLimitUpdate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return update_client_credit(
        client_id,
        data,
        db,
        cast(int, user_tenant.tenant_id),
        current_user,
    )


@portfolio_routes.get(
    "/obligations",
    response_model=list[ObligationRead],
    dependencies=[Depends(require_permission("PORTFOLIO_READ"))],
)
async def list_obligations_route(
    client_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return obligations(
        db,
        cast(int, user_tenant.tenant_id),
        client_id=client_id,
        date_from=date_from,
        date_to=date_to,
    )


@portfolio_routes.get(
    "/clients/{client_id}/obligations",
    response_model=list[ObligationRead],
    dependencies=[Depends(require_permission("PORTFOLIO_READ"))],
)
async def list_client_obligations_route(
    client_id: UUID,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return client_obligations(client_id, db, cast(int, user_tenant.tenant_id))


@portfolio_routes.post(
    "/payments",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_permission("PORTFOLIO_PAYMENT_CREATE")),
        Depends(require_operational_cash_context),
    ],
)
async def create_payment_route(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return create_payment(data, db, cast(int, user_tenant.tenant_id), current_user)


@portfolio_routes.post(
    "/payments/{payment_id}/annul",
    response_model=PaymentRead,
    dependencies=[
        Depends(require_permission("PORTFOLIO_PAYMENT_CREATE")),
        Depends(require_operational_cash_context),
    ],
)
async def annul_payment_endpoint(
    payment_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return annul_payment_route(
        payment_id,
        db,
        cast(int, user_tenant.tenant_id),
        current_user,
    )


@portfolio_routes.get(
    "/payments",
    response_model=list[PaymentRead],
    dependencies=[Depends(require_permission("PORTFOLIO_READ"))],
)
async def list_payments_route(
    client_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    payment_status: str | None = Query(None, alias="status", pattern="^(APLICADO|ANULADO)$"),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return payments(
        db,
        cast(int, user_tenant.tenant_id),
        client_id=client_id,
        date_from=date_from,
        date_to=date_to,
        payment_status=payment_status,
    )
