import os
import secrets
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from UsersAPI.domains.core.database import get_db
from UsersAPI.domains.core.models import UserTenantDB
from UsersAPI.security.dependencies import get_current_tenant
from UsersAPI.security.permissions import require_permission

from ..schemas.screening import ClientScreeningRead
from ..services.screening_provider import sync_all_screening_lists
from ..services.screening_report_service import list_screenings


screening_routes = APIRouter(
    prefix="/clients/screenings",
    tags=["Clientes - Listas Restrictivas"],
)


def _require_sync_key(x_job_key: str | None = Header(default=None, alias="X-Job-Key")) -> None:
    expected = os.getenv("CLIENT_SCREENING_SYNC_KEY")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La sincronización de listas no está configurada.",
        )
    if not x_job_key or not secrets.compare_digest(x_job_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial de sincronización inválida.",
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


@screening_routes.post(
    "/sync",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(_require_sync_key)],
)
async def sync_screening_lists_route(db: Session = Depends(get_db)):
    return sync_all_screening_lists(db)
