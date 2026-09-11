from typing import cast

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from UsersAPI.domains.core.controllers import get_current_user
from UsersAPI.domains.core.database import get_db
from UsersAPI.domains.core.models import UserTenantDB
from UsersAPI.security.dependencies import get_current_tenant
from UsersAPI.security.permissions import require_permission

from ..controllers import (
    add_movement,
    close_register,
    current_register,
    get_register,
    list_registers,
    open_register,
    register_summary,
)
from ..models import BranchDB, CashBoxDB
from ..schemas import (
    BranchCreate,
    BranchRead,
    BranchUpdate,
    CashAssignmentCreate,
    CashAssignmentRead,
    CashBoxCreate,
    CashBoxRead,
    CashBoxUpdate,
    CashContextRead,
    CashMovementCreate,
    CashRegisterClose,
    CashRegisterOpen,
    CashRegisterRead,
    CashRegisterSummary,
)
from ..services import (
    create_assignment,
    create_branch,
    create_cash_box,
    get_user_cash_context,
    list_assignments,
    list_branches,
    list_cash_boxes,
    unassign,
    update_branch,
    update_cash_box,
)

cash_routes = APIRouter(prefix="/cash", tags=["Caja"])


def _read_register(db: Session, tenant_id: int, register_id: int) -> CashRegisterRead:
    register = get_register(db, tenant_id, register_id)
    summary = register_summary(db, tenant_id, register_id)
    return CashRegisterRead.model_validate(
        {
            **register.__dict__,
            "movements": register.movements,
            "summary": summary,
            "expected_cash": summary["expected_cash"],
            "counted_cash": summary["counted_cash"],
            "difference": summary["difference"],
        }
    )


def _tenant_id(user_tenant: UserTenantDB) -> int:
    return cast(int, user_tenant.tenant_id)


def _branch_response(branch, cash_boxes_count: int | None = None) -> dict:
    values = branch if isinstance(branch, dict) else branch.__dict__
    return {
        "id": values.get("id"),
        "tenant_id": values.get("tenant_id"),
        "code": values.get("code"),
        "name": values.get("name"),
        "address": values.get("address"),
        "phone": values.get("phone"),
        "status": values.get("status"),
        "created_at": values.get("created_at"),
        "created_by": values.get("created_by"),
        "updated_at": values.get("updated_at"),
        "updated_by": values.get("updated_by"),
        "cash_boxes_count": values.get(
            "cash_boxes_count", cash_boxes_count if cash_boxes_count is not None else 0
        ),
    }


@cash_routes.get("/my-context", response_model=CashContextRead)
async def my_cash_context_route(
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return get_user_cash_context(db, _tenant_id(user_tenant), cast(int, current_user.id))


@cash_routes.get(
    "/config/branches",
    response_model=list[BranchRead],
    dependencies=[Depends(require_permission("CASH_READ"))],
)
async def list_branches_route(
    db: Session = Depends(get_db), user_tenant: UserTenantDB = Depends(get_current_tenant)
):
    return [_branch_response(branch) for branch in list_branches(db, _tenant_id(user_tenant))]


@cash_routes.post(
    "/config/branches",
    response_model=BranchRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("CASH_CREATE"))],
)
async def create_branch_route(
    data: BranchCreate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    branch = create_branch(data, db, _tenant_id(user_tenant), current_user)
    return _branch_response(branch, 0)


@cash_routes.patch(
    "/config/branches/{branch_id}",
    response_model=BranchRead,
    dependencies=[Depends(require_permission("CASH_CREATE"))],
)
async def update_branch_route(
    branch_id: int,
    data: BranchUpdate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    branch = update_branch(branch_id, data, db, _tenant_id(user_tenant), current_user)
    cash_boxes_count = db.scalar(
        select(func.count(CashBoxDB.id)).where(
            CashBoxDB.tenant_id == _tenant_id(user_tenant), CashBoxDB.branch_id == branch.id
        )
    )
    return _branch_response(branch, int(cash_boxes_count or 0))


@cash_routes.get(
    "/config/boxes",
    response_model=list[CashBoxRead],
    dependencies=[Depends(require_permission("CASH_READ"))],
)
async def list_cash_boxes_route(
    branch_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return list_cash_boxes(db, _tenant_id(user_tenant), branch_id)


@cash_routes.post(
    "/config/boxes",
    response_model=CashBoxRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("CASH_CREATE"))],
)
async def create_cash_box_route(
    data: CashBoxCreate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    cash_box = create_cash_box(data, db, _tenant_id(user_tenant), current_user)
    branch_name = db.scalar(
        select(BranchDB.name).where(
            BranchDB.tenant_id == _tenant_id(user_tenant), BranchDB.id == data.branch_id
        )
    )
    return {**cash_box.__dict__, "branch_name": branch_name}


@cash_routes.patch(
    "/config/boxes/{cash_box_id}",
    response_model=CashBoxRead,
    dependencies=[Depends(require_permission("CASH_CREATE"))],
)
async def update_cash_box_route(
    cash_box_id: int,
    data: CashBoxUpdate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    cash_box = update_cash_box(cash_box_id, data, db, _tenant_id(user_tenant), current_user)
    rows = list_cash_boxes(db, _tenant_id(user_tenant), cash_box.branch_id)
    return next(row for row in rows if row["id"] == cash_box.id)


@cash_routes.get(
    "/config/assignments",
    response_model=list[CashAssignmentRead],
    dependencies=[Depends(require_permission("CASH_READ"))],
)
async def list_assignments_route(
    db: Session = Depends(get_db), user_tenant: UserTenantDB = Depends(get_current_tenant)
):
    return list_assignments(db, _tenant_id(user_tenant))


@cash_routes.post(
    "/config/assignments",
    response_model=CashAssignmentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("CASH_CREATE"))],
)
async def create_assignment_route(
    data: CashAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    assignment = create_assignment(data, db, _tenant_id(user_tenant), current_user)
    return next(
        item
        for item in list_assignments(db, _tenant_id(user_tenant))
        if item["id"] == assignment.id
    )


@cash_routes.delete(
    "/config/assignments/{assignment_id}",
    response_model=CashAssignmentRead,
    dependencies=[Depends(require_permission("CASH_CREATE"))],
)
async def unassign_route(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    unassign(assignment_id, db, _tenant_id(user_tenant), current_user)
    return next(
        item
        for item in list_assignments(db, _tenant_id(user_tenant))
        if item["id"] == assignment_id
    )


@cash_routes.post(
    "/registers/open",
    response_model=CashRegisterRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("CASH_CREATE"))],
)
async def open_register_route(
    data: CashRegisterOpen,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    tenant_id = _tenant_id(user_tenant)
    register = open_register(data, db, tenant_id, current_user)
    return _read_register(db, tenant_id, register.id)


@cash_routes.get(
    "/registers/current",
    response_model=CashRegisterRead,
    dependencies=[Depends(require_permission("CASH_READ"))],
)
async def current_register_route(
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    tenant_id = _tenant_id(user_tenant)
    register = current_register(db, tenant_id, current_user)
    return _read_register(db, tenant_id, register.id)


@cash_routes.get(
    "/registers",
    response_model=list[CashRegisterRead],
    dependencies=[Depends(require_permission("CASH_READ"))],
)
async def list_registers_route(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    tenant_id = _tenant_id(user_tenant)
    registers = list_registers(db, tenant_id, limit=limit, offset=offset)
    return [_read_register(db, tenant_id, register.id) for register in registers]


@cash_routes.get(
    "/registers/{register_id}",
    response_model=CashRegisterRead,
    dependencies=[Depends(require_permission("CASH_READ"))],
)
async def get_register_route(
    register_id: int,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return _read_register(db, _tenant_id(user_tenant), register_id)


@cash_routes.post(
    "/registers/{register_id}/movements",
    response_model=CashRegisterRead,
    dependencies=[Depends(require_permission("CASH_MOVEMENT_CREATE"))],
)
async def add_movement_route(
    register_id: int,
    data: CashMovementCreate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    tenant_id = _tenant_id(user_tenant)
    add_movement(data, db, tenant_id, register_id, current_user)
    return _read_register(db, tenant_id, register_id)


@cash_routes.post(
    "/registers/{register_id}/close",
    response_model=CashRegisterRead,
    dependencies=[Depends(require_permission("CASH_CLOSE"))],
)
async def close_register_route(
    register_id: int,
    data: CashRegisterClose,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    tenant_id = _tenant_id(user_tenant)
    close_register(data, db, tenant_id, register_id, current_user)
    return _read_register(db, tenant_id, register_id)


@cash_routes.get(
    "/registers/{register_id}/summary",
    response_model=CashRegisterSummary,
    dependencies=[Depends(require_permission("CASH_READ"))],
)
async def register_summary_route(
    register_id: int,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return register_summary(db, _tenant_id(user_tenant), register_id)
