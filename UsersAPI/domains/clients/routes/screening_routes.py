import secrets
from typing import cast
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from UsersAPI.controllers.auth_controller import get_current_user
from UsersAPI.domains.core.database import get_db
from UsersAPI.domains.core.models import GlobalUserDB, UserTenantDB
from UsersAPI.security.dependencies import get_current_tenant
from UsersAPI.security.permissions import require_permission
from UsersAPI.settings import settings

from ..schemas.screening import ClientScreeningRead
from ..schemas.screening_sync import (
    ScreeningSyncExecutionAccepted,
    ScreeningSyncExecutionRead,
)
from ..services.screening_report_service import list_screenings
from ..services.screening_sync_service import (
    create_sync_execution,
    list_sync_executions,
    run_sync_execution,
)


screening_routes = APIRouter(
    prefix="/clients/screenings",
    tags=["Clientes - Listas Restrictivas"],
)


def _require_sync_key(x_job_key: str | None = Header(default=None, alias="X-Job-Key")) -> None:
    expected = settings.client_screening_sync_key
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


@screening_routes.get(
    "/sync/executions",
    response_model=list[ScreeningSyncExecutionRead],
    dependencies=[Depends(require_permission("CLIENT_SCREENING"))],
)
async def list_sync_executions_route(db: Session = Depends(get_db)):
    return list_sync_executions(db)


def _accepted(execution, message: str) -> ScreeningSyncExecutionAccepted:
    return ScreeningSyncExecutionAccepted(
        id=execution.id,
        status=execution.status,
        message=message,
    )


@screening_routes.post(
    "/sync",
    response_model=ScreeningSyncExecutionAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(_require_sync_key)],
)
async def sync_screening_lists_route(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    execution = create_sync_execution(db, trigger_type="CRONJOB")
    if execution.status == "PENDING":
        background_tasks.add_task(run_sync_execution, execution.id)
    return _accepted(execution, "Sincronización de listas programada correctamente.")


@screening_routes.post(
    "/sync/manual",
    response_model=ScreeningSyncExecutionAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permission("CLIENT_SCREENING"))],
)
async def manual_sync_screening_lists_route(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserTenantDB | GlobalUserDB = Depends(get_current_user),
):
    execution = create_sync_execution(
        db,
        trigger_type="MANUAL",
        triggered_by=current_user.id,
        triggered_by_email=getattr(current_user, "email", None),
    )
    if execution.status == "PENDING":
        background_tasks.add_task(run_sync_execution, execution.id)
    return _accepted(execution, "Sincronización manual de listas programada correctamente.")
