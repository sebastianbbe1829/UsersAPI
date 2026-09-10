from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from UsersAPI.domains.core.models import UserDB, UserTenantDB

from ..models import BranchDB, CashBoxDB, UserCashAssignmentDB
from ..schemas import (
    BranchCreate,
    BranchUpdate,
    CashAssignmentCreate,
    CashBoxCreate,
    CashBoxUpdate,
)


def _actor_name(current_user) -> str:
    return str(
        getattr(current_user, "email", None)
        or getattr(current_user, "username", None)
        or getattr(current_user, "id", "system")
    )[:100]


def _conflict(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)


def _branch(db: Session, tenant_id: int, branch_id: int) -> BranchDB:
    branch = db.scalar(
        select(BranchDB).where(
            BranchDB.tenant_id == tenant_id,
            BranchDB.id == branch_id,
        )
    )
    if branch is None:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")
    return branch


def _cash_box(db: Session, tenant_id: int, cash_box_id: int) -> CashBoxDB:
    cash_box = db.scalar(
        select(CashBoxDB).where(
            CashBoxDB.tenant_id == tenant_id,
            CashBoxDB.id == cash_box_id,
        )
    )
    if cash_box is None:
        raise HTTPException(status_code=404, detail="Caja física no encontrada.")
    return cash_box


def list_branches(db: Session, tenant_id: int) -> list[dict]:
    rows = db.execute(
        select(
            BranchDB,
            func.count(CashBoxDB.id).label("cash_boxes_count"),
        )
        .outerjoin(
            CashBoxDB,
            (CashBoxDB.tenant_id == BranchDB.tenant_id) & (CashBoxDB.branch_id == BranchDB.id),
        )
        .where(BranchDB.tenant_id == tenant_id)
        .group_by(BranchDB.id)
        .order_by(BranchDB.id)
    ).all()
    return [
        {
            **branch.__dict__,
            "cash_boxes_count": int(count or 0),
        }
        for branch, count in rows
    ]


def create_branch(data: BranchCreate, db: Session, tenant_id: int, current_user) -> BranchDB:
    code = data.code.strip().upper()
    if db.scalar(
        select(BranchDB.id).where(
            BranchDB.tenant_id == tenant_id,
            func.upper(BranchDB.code) == code,
        )
    ):
        raise _conflict("Ya existe una sucursal con ese código.")
    branch = BranchDB(
        tenant_id=tenant_id,
        code=code,
        name=data.name.strip(),
        address=data.address.strip() if data.address else None,
        phone=data.phone.strip() if data.phone else None,
        status=1,
        created_by=_actor_name(current_user),
    )
    db.add(branch)
    db.flush()
    return branch


def update_branch(
    branch_id: int,
    data: BranchUpdate,
    db: Session,
    tenant_id: int,
    current_user,
) -> BranchDB:
    branch = _branch(db, tenant_id, branch_id)
    changes = data.model_dump(exclude_unset=True)
    if "code" in changes and changes["code"] is not None:
        code = changes["code"].strip().upper()
        duplicate = db.scalar(
            select(BranchDB.id).where(
                BranchDB.tenant_id == tenant_id,
                func.upper(BranchDB.code) == code,
                BranchDB.id != branch_id,
            )
        )
        if duplicate is not None:
            raise _conflict("Ya existe una sucursal con ese código.")
        branch.code = code
    if "name" in changes and changes["name"] is not None:
        branch.name = changes["name"].strip()
    if "address" in changes:
        branch.address = changes["address"].strip() if changes["address"] else None
    if "phone" in changes:
        branch.phone = changes["phone"].strip() if changes["phone"] else None
    if "status" in changes and changes["status"] is not None:
        branch.status = changes["status"]
    branch.updated_at = datetime.now()
    branch.updated_by = _actor_name(current_user)
    db.flush()
    return branch


def list_cash_boxes(db: Session, tenant_id: int, branch_id: int | None = None) -> list[dict]:
    query = (
        select(CashBoxDB, BranchDB.name.label("branch_name"))
        .join(
            BranchDB,
            (BranchDB.tenant_id == CashBoxDB.tenant_id) & (BranchDB.id == CashBoxDB.branch_id),
        )
        .where(CashBoxDB.tenant_id == tenant_id)
        .order_by(CashBoxDB.branch_id, CashBoxDB.id)
    )
    if branch_id is not None:
        query = query.where(CashBoxDB.branch_id == branch_id)
    return [
        {**cash_box.__dict__, "branch_name": branch_name}
        for cash_box, branch_name in db.execute(query).all()
    ]


def create_cash_box(data: CashBoxCreate, db: Session, tenant_id: int, current_user) -> CashBoxDB:
    branch = _branch(db, tenant_id, data.branch_id)
    if branch.status != 1:
        raise _conflict("No se puede crear una caja física en una sucursal inactiva.")
    code = data.code.strip().upper()
    if db.scalar(
        select(CashBoxDB.id).where(
            CashBoxDB.tenant_id == tenant_id,
            CashBoxDB.branch_id == data.branch_id,
            func.upper(CashBoxDB.code) == code,
        )
    ):
        raise _conflict("Ya existe una caja con ese código en la sucursal.")
    cash_box = CashBoxDB(
        tenant_id=tenant_id,
        branch_id=data.branch_id,
        code=code,
        name=data.name.strip(),
        status=1,
        created_by=_actor_name(current_user),
    )
    db.add(cash_box)
    db.flush()
    return cash_box


def update_cash_box(
    cash_box_id: int,
    data: CashBoxUpdate,
    db: Session,
    tenant_id: int,
    current_user,
) -> CashBoxDB:
    cash_box = _cash_box(db, tenant_id, cash_box_id)
    changes = data.model_dump(exclude_unset=True)
    if "code" in changes and changes["code"] is not None:
        code = changes["code"].strip().upper()
        duplicate = db.scalar(
            select(CashBoxDB.id).where(
                CashBoxDB.tenant_id == tenant_id,
                CashBoxDB.branch_id == cash_box.branch_id,
                func.upper(CashBoxDB.code) == code,
                CashBoxDB.id != cash_box_id,
            )
        )
        if duplicate is not None:
            raise _conflict("Ya existe una caja con ese código en la sucursal.")
        cash_box.code = code
    if "name" in changes and changes["name"] is not None:
        cash_box.name = changes["name"].strip()
    if "status" in changes and changes["status"] is not None:
        cash_box.status = changes["status"]
    cash_box.updated_at = datetime.now()
    cash_box.updated_by = _actor_name(current_user)
    db.flush()
    return cash_box


def list_assignments(db: Session, tenant_id: int) -> list[dict]:
    query = (
        select(
            UserCashAssignmentDB,
            UserDB.name.label("user_name"),
            UserDB.dni.label("user_dni"),
            UserTenantDB.email.label("user_email"),
            BranchDB.name.label("branch_name"),
            CashBoxDB.name.label("cash_box_name"),
            CashBoxDB.code.label("cash_box_code"),
        )
        .join(
            UserTenantDB,
            (UserTenantDB.tenant_id == UserCashAssignmentDB.tenant_id)
            & (UserTenantDB.id == UserCashAssignmentDB.user_tenant_id),
        )
        .join(UserDB, UserDB.id == UserTenantDB.user_id)
        .join(
            BranchDB,
            (BranchDB.tenant_id == UserCashAssignmentDB.tenant_id)
            & (BranchDB.id == UserCashAssignmentDB.branch_id),
        )
        .join(
            CashBoxDB,
            (CashBoxDB.tenant_id == UserCashAssignmentDB.tenant_id)
            & (CashBoxDB.id == UserCashAssignmentDB.cash_box_id),
        )
        .where(UserCashAssignmentDB.tenant_id == tenant_id)
        .order_by(UserCashAssignmentDB.status.desc(), UserCashAssignmentDB.id.desc())
    )
    return [
        {
            **assignment.__dict__,
            "user_name": user_name,
            "user_dni": user_dni,
            "user_email": user_email,
            "branch_name": branch_name,
            "cash_box_name": cash_box_name,
            "cash_box_code": cash_box_code,
        }
        for (
            assignment,
            user_name,
            user_dni,
            user_email,
            branch_name,
            cash_box_name,
            cash_box_code,
        ) in db.execute(query).all()
    ]


def create_assignment(
    data: CashAssignmentCreate,
    db: Session,
    tenant_id: int,
    current_user,
) -> UserCashAssignmentDB:
    user_tenant = db.scalar(
        select(UserTenantDB).where(
            UserTenantDB.tenant_id == tenant_id,
            UserTenantDB.id == data.user_tenant_id,
            UserTenantDB.status == 1,
        )
    )
    if user_tenant is None:
        raise HTTPException(status_code=404, detail="Usuario activo no encontrado.")

    branch = _branch(db, tenant_id, data.branch_id)
    if branch.status != 1:
        raise _conflict("La sucursal seleccionada está inactiva.")

    cash_box = _cash_box(db, tenant_id, data.cash_box_id)
    if cash_box.branch_id != data.branch_id:
        raise _conflict("La caja física no pertenece a la sucursal seleccionada.")
    if cash_box.status != 1:
        raise _conflict("La caja física seleccionada está inactiva.")

    existing = db.scalar(
        select(UserCashAssignmentDB).where(
            UserCashAssignmentDB.tenant_id == tenant_id,
            UserCashAssignmentDB.user_tenant_id == data.user_tenant_id,
            UserCashAssignmentDB.status == 1,
        )
    )
    if existing is not None:
        raise _conflict(
            "El usuario ya tiene una sucursal y caja asignadas. Primero desasigna la actual."
        )

    assignment = UserCashAssignmentDB(
        tenant_id=tenant_id,
        user_tenant_id=data.user_tenant_id,
        branch_id=data.branch_id,
        cash_box_id=data.cash_box_id,
        status=1,
        assigned_by=_actor_name(current_user),
    )
    db.add(assignment)
    db.flush()
    return assignment


def unassign(
    assignment_id: int,
    db: Session,
    tenant_id: int,
    current_user,
) -> UserCashAssignmentDB:
    assignment = db.scalar(
        select(UserCashAssignmentDB).where(
            UserCashAssignmentDB.tenant_id == tenant_id,
            UserCashAssignmentDB.id == assignment_id,
            UserCashAssignmentDB.status == 1,
        )
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Asignación activa no encontrada.")
    assignment.status = 0
    assignment.unassigned_at = datetime.now()
    assignment.unassigned_by = _actor_name(current_user)
    db.flush()
    return assignment
