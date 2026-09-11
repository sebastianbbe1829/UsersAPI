from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from UsersAPI.domains.cash.services.cash_dependencies import require_operational_cash_context
from UsersAPI.domains.core.controllers import get_current_user
from UsersAPI.domains.core.database import get_db
from UsersAPI.domains.core.models import UserTenantDB
from UsersAPI.security.dependencies import get_current_tenant
from UsersAPI.security.permissions import require_permission

from ..controllers import (
    create,
    create_frozen,
    delete_frozen,
    get,
    get_frozen,
    list_all,
    list_frozen,
)
from ..schemas import (
    SaleCreate,
    SaleDraftCreate,
    SaleDraftRead,
    SaleRead,
    SalesPOSCatalogRead,
    SalesPOSClientRead,
    SalesPOSCreditRead,
)
from ..services import get_pos_catalog, get_pos_client_credit, search_pos_clients
from ..services.invoice_service import send_invoice_email

sales_routes = APIRouter(prefix="/sales", tags=["Ventas"])


@sales_routes.get(
    "/pos/catalog",
    response_model=SalesPOSCatalogRead,
    dependencies=[Depends(require_permission("SALES_CREATE"))],
)
async def get_sales_pos_catalog_route(
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return get_pos_catalog(db, cast(int, user_tenant.tenant_id))


@sales_routes.get(
    "/pos/clients",
    response_model=list[SalesPOSClientRead],
    dependencies=[Depends(require_permission("SALES_CREATE"))],
)
async def search_sales_pos_clients_route(
    search: str | None = Query(None, max_length=100),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    clients = search_pos_clients(
        db,
        cast(int, user_tenant.tenant_id),
        search=search,
        limit=limit,
        offset=offset,
    )
    return [
        SalesPOSClientRead(
            id=str(client.id),
            full_name=client.full_name,
            identification_number=client.identification_number,
            status=client.status,
            email=str(client.email) if client.email else None,
        )
        for client in clients
    ]


@sales_routes.get(
    "/pos/clients/{client_id}/credit",
    response_model=SalesPOSCreditRead,
    dependencies=[Depends(require_permission("SALES_CREATE"))],
)
async def get_sales_pos_client_credit_route(
    client_id: UUID,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    credit = get_pos_client_credit(client_id, db, cast(int, user_tenant.tenant_id))
    return SalesPOSCreditRead(
        client_id=str(client_id),
        approved_limit=float(credit.approved_limit),
        credit_used=float(credit.credit_used),
        credit_available=float(credit.credit_available),
    )


@sales_routes.post(
    "",
    response_model=SaleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_permission("SALES_CREATE")),
        Depends(require_operational_cash_context),
    ],
)
async def create_sale_route(
    data: SaleCreate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return create(data, db, cast(int, user_tenant.tenant_id), current_user)


@sales_routes.post(
    "/autoconsumption",
    response_model=SaleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_permission("SALES_AUTOCONSUME")),
        Depends(require_operational_cash_context),
    ],
)
async def create_autoconsumption_sale_route(
    data: SaleCreate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return create(
        data,
        db,
        cast(int, user_tenant.tenant_id),
        current_user,
        is_autoconsumption=True,
    )


@sales_routes.post(
    "/drafts",
    response_model=SaleDraftRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("SALES_CREATE"))],
)
async def create_frozen_sale_route(
    data: SaleDraftCreate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return create_frozen(data, db, cast(int, user_tenant.tenant_id), current_user)


@sales_routes.post(
    "/drafts/autoconsumption",
    response_model=SaleDraftRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("SALES_AUTOCONSUME"))],
)
async def create_frozen_autoconsumption_route(
    data: SaleDraftCreate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return create_frozen(
        data,
        db,
        cast(int, user_tenant.tenant_id),
        current_user,
        is_autoconsumption=True,
    )


@sales_routes.get(
    "/drafts",
    response_model=list[SaleDraftRead],
    dependencies=[Depends(require_permission("SALES_CREATE"))],
)
async def list_frozen_sales_route(
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return list_frozen(db, cast(int, user_tenant.tenant_id))


@sales_routes.get(
    "/drafts/{draft_id}",
    response_model=SaleDraftRead,
    dependencies=[Depends(require_permission("SALES_CREATE"))],
)
async def get_frozen_sale_route(
    draft_id: UUID,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return get_frozen(draft_id, db, cast(int, user_tenant.tenant_id))


@sales_routes.delete(
    "/drafts/{draft_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("SALES_CREATE"))],
)
async def delete_frozen_sale_route(
    draft_id: UUID,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    delete_frozen(draft_id, db, cast(int, user_tenant.tenant_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@sales_routes.get(
    "",
    response_model=list[SaleRead],
    dependencies=[Depends(require_permission("SALES_READ"))],
)
async def list_sales_route(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return list_all(db, cast(int, user_tenant.tenant_id), limit=limit, offset=offset)


@sales_routes.get(
    "/{sale_id}",
    response_model=SaleRead,
    dependencies=[Depends(require_permission("SALES_READ"))],
)
async def get_sale_route(
    sale_id: UUID,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return get(sale_id, db, cast(int, user_tenant.tenant_id))


@sales_routes.post(
    "/{sale_id}/invoice/email",
    response_model=dict,
    dependencies=[Depends(require_permission("SALES_EMAIL"))],
)
async def email_invoice_route(
    sale_id: UUID,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    recipients = send_invoice_email(sale_id, db, cast(int, user_tenant.tenant_id))
    return {"message": "Invoice sent successfully", "recipients": recipients}
