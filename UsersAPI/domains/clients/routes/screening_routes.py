from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from UsersAPI.domains.core.database import get_db
from UsersAPI.domains.core.models import UserTenantDB
from UsersAPI.security.permissions import require_permission
from UsersAPI.security.dependencies import get_current_tenant

from ..schemas.screening import ClientScreeningRead
from ..services.screening_report_service import list_screenings


screening_routes = APIRouter(
    prefix="/clients/screenings",
    tags=["Clientes - Listas Restrictivas"],
)


@screening_routes.get(
    "",
    response_model=list[ClientScreeningRead],
    dependencies=[Depends(require_permission("CLIENT_SCREENING"))],
)
async def list_screenings_route(
    client_id: UUID | None = None,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return list_screenings(db, cast(int, user_tenant.tenant_id), client_id)
