from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from UsersAPI.domains.core.controllers import get_current_user
from UsersAPI.domains.core.database import get_db
from UsersAPI.domains.core.models import UserTenantDB
from UsersAPI.security.dependencies import get_current_tenant
from UsersAPI.security.permissions import require_permission

from ..schemas import CashDayClose, CashDayRead, CashDayStart, CashRegisterClose
from ..services import (
    close_branch,
    close_day,
    close_register,
    get_current_day,
    serialize_day,
    start_day,
)
from ..services.cash_day_report_service import build_day_report, excel_report, pdf_report

cash_day_routes = APIRouter(prefix="/days", tags=["Caja - Día operativo"])


def _tenant_id(user_tenant: UserTenantDB) -> int:
    return int(user_tenant.tenant_id)


@cash_day_routes.post(
    "/start",
    response_model=CashDayRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("CASH_DAY_START"))],
)
async def start_day_route(
    data: CashDayStart,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    day = start_day(db, _tenant_id(user_tenant), data.business_date, current_user)
    return serialize_day(db, day)


@cash_day_routes.get(
    "/current",
    response_model=CashDayRead | None,
    dependencies=[Depends(require_permission("CASH_READ"))],
)
async def current_day_route(
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    day = get_current_day(db, _tenant_id(user_tenant))
    return None if day is None else serialize_day(db, day)


@cash_day_routes.get(
    "/{day_id}/report/{file_format}",
    dependencies=[Depends(require_permission("CASH_READ"))],
)
async def day_report_route(
    day_id: int,
    file_format: str,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    tenant_id = _tenant_id(user_tenant)
    try:
        report = build_day_report(db, tenant_id, day_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    normalized = file_format.strip().lower()
    if normalized == "pdf":
        content, filename = pdf_report(report)
        media_type = "application/pdf"
    elif normalized in {"xlsx", "excel"}:
        content, filename = excel_report(report)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        raise HTTPException(status_code=400, detail="Formato de reporte no soportado. Usa pdf o xlsx.")

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@cash_day_routes.get(
    "/current/report/{file_format}",
    dependencies=[Depends(require_permission("CASH_READ"))],
)
async def current_day_report_route(
    file_format: str,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    day = get_current_day(db, _tenant_id(user_tenant))
    if day is None:
        raise HTTPException(status_code=404, detail="No existe un día operativo para generar el reporte.")
    return await day_report_route(file_format=file_format, day_id=day.id, db=db, user_tenant=user_tenant)


@cash_day_routes.post(
    "/registers/{register_id}/close",
    response_model=CashDayRead,
    dependencies=[Depends(require_permission("CASH_CLOSE"))],
)
async def close_day_register_route(
    register_id: int,
    data: CashRegisterClose,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    tenant_id = _tenant_id(user_tenant)
    close_register(db, tenant_id, register_id, data.counted_cash, data.closing_notes, current_user)
    day = get_current_day(db, tenant_id)
    return serialize_day(db, day)


@cash_day_routes.post(
    "/branches/{branch_id}/close",
    response_model=CashDayRead,
    dependencies=[Depends(require_permission("CASH_BRANCH_CLOSE"))],
)
async def close_day_branch_route(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    tenant_id = _tenant_id(user_tenant)
    close_branch(db, tenant_id, branch_id, current_user)
    day = get_current_day(db, tenant_id)
    return serialize_day(db, day)


@cash_day_routes.post(
    "/close",
    response_model=CashDayRead,
    dependencies=[Depends(require_permission("CASH_DAY_CLOSE"))],
)
async def close_day_route(
    data: CashDayClose,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    tenant_id = _tenant_id(user_tenant)
    day = close_day(db, tenant_id, current_user)
    day.closing_notes = data.closing_notes
    db.flush()
    return serialize_day(db, day)
