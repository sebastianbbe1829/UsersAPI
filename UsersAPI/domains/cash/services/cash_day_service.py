from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models import BranchDB, CashBoxDB, CashDayBranchDB, CashDayDB, CashRegisterDB


def _actor_name(current_user: object | None) -> str:
    return str(
        getattr(current_user, "email", None)
        or getattr(current_user, "username", None)
        or getattr(current_user, "id", "system")
    )[:100]


def get_current_day(db: Session, tenant_id: int) -> CashDayDB | None:
    day = db.scalar(
        select(CashDayDB)
        .where(
            CashDayDB.tenant_id == tenant_id,
            CashDayDB.status == "OPEN",
        )
        .options(
            joinedload(CashDayDB.branches).joinedload(CashDayBranchDB.branch),
            joinedload(CashDayDB.registers),
        )
        .order_by(CashDayDB.business_date.desc(), CashDayDB.id.desc())
    )
    if day is not None:
        return day

    return db.scalar(
        select(CashDayDB)
        .where(CashDayDB.tenant_id == tenant_id)
        .options(
            joinedload(CashDayDB.branches).joinedload(CashDayBranchDB.branch),
            joinedload(CashDayDB.registers),
        )
        .order_by(CashDayDB.business_date.desc(), CashDayDB.id.desc())
    )


def get_day_by_date(db: Session, tenant_id: int, business_date: date) -> CashDayDB | None:
    return db.scalar(
        select(CashDayDB)
        .where(
            CashDayDB.tenant_id == tenant_id,
            CashDayDB.business_date == business_date,
        )
        .options(
            joinedload(CashDayDB.branches).joinedload(CashDayBranchDB.branch),
            joinedload(CashDayDB.registers),
        )
    )


def require_open_day(db: Session, tenant_id: int) -> CashDayDB:
    day = db.scalar(
        select(CashDayDB)
        .where(
            CashDayDB.tenant_id == tenant_id,
            CashDayDB.status == "OPEN",
        )
        .order_by(CashDayDB.business_date.desc(), CashDayDB.id.desc())
    )
    if day is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CASH_DAY_NOT_STARTED",
                "message": "El día operativo no ha sido iniciado.",
            },
        )
    return day


def start_day(
    db: Session,
    tenant_id: int,
    business_date: date,
    current_user: object,
) -> CashDayDB:
    open_day = db.scalar(
        select(CashDayDB.id).where(
            CashDayDB.tenant_id == tenant_id,
            CashDayDB.status == "OPEN",
        )
    )
    if open_day is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CASH_DAY_ALREADY_OPEN",
                "message": "Ya existe un día operativo abierto para el tenant.",
            },
        )

    last_day_date = db.scalar(
        select(CashDayDB.business_date)
        .where(CashDayDB.tenant_id == tenant_id)
        .order_by(CashDayDB.business_date.desc(), CashDayDB.id.desc())
        .limit(1)
    )
    if last_day_date is not None and business_date <= last_day_date:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CASH_DAY_DATE_MUST_ADVANCE",
                "message": (
                    f"La fecha de operación debe ser posterior al último día operativo "
                    f"registrado ({last_day_date.isoformat()})."
                ),
            },
        )

    existing = db.scalar(
        select(CashDayDB).where(
            CashDayDB.tenant_id == tenant_id,
            CashDayDB.business_date == business_date,
        )
    )
    if existing is not None:
        if existing.status == "CLOSED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "CASH_DAY_ALREADY_CLOSED",
                    "message": "La fecha de operación ya fue cerrada y no puede reabrirse.",
                },
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CASH_DAY_ALREADY_STARTED",
                "message": "La fecha de operación ya fue iniciada.",
            },
        )

    actor = _actor_name(current_user)
    active_branches = db.scalars(
        select(BranchDB)
        .where(BranchDB.tenant_id == tenant_id, BranchDB.status == 1)
        .order_by(BranchDB.id)
        .with_for_update()
    ).all()
    active_branch_ids = [branch.id for branch in active_branches]
    active_boxes_query = select(CashBoxDB).where(
        CashBoxDB.tenant_id == tenant_id,
        CashBoxDB.status == 1,
    )
    if active_branch_ids:
        active_boxes_query = active_boxes_query.where(CashBoxDB.branch_id.in_(active_branch_ids))
    else:
        active_boxes_query = active_boxes_query.where(CashBoxDB.id == -1)
    active_boxes = db.scalars(
        active_boxes_query.order_by(CashBoxDB.id).with_for_update()
    ).all()

    day = CashDayDB(
        tenant_id=tenant_id,
        business_date=business_date,
        status="OPEN",
        opened_by=actor,
    )
    db.add(day)
    db.flush()

    for branch in active_branches:
        db.add(
            CashDayBranchDB(
                tenant_id=tenant_id,
                cash_day_id=day.id,
                branch_id=branch.id,
                status="OPEN",
                opened_by=actor,
            )
        )

    for box in active_boxes:
        base_amount = Decimal(str(box.base_amount or 0))
        db.add(
            CashRegisterDB(
                tenant_id=tenant_id,
                cash_day_id=day.id,
                branch_id=box.branch_id,
                cash_box_id=box.id,
                business_date=business_date,
                opened_by=actor,
                opening_amount=base_amount,
                status="OPEN",
            )
        )

    db.flush()
    return day


def close_register(
    db: Session,
    tenant_id: int,
    register_id: int,
    counted_cash: Decimal,
    closing_notes: str | None,
    current_user: object,
) -> CashRegisterDB:
    register = db.scalar(
        select(CashRegisterDB)
        .where(CashRegisterDB.tenant_id == tenant_id, CashRegisterDB.id == register_id)
        .with_for_update()
    )
    if register is None:
        raise HTTPException(status_code=404, detail="Caja no encontrada.")

    day = require_open_day(db, tenant_id)
    if register.cash_day_id != day.id:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CASH_REGISTER_NOT_CURRENT_DAY",
                "message": "La caja no pertenece al día operativo abierto.",
            },
        )
    if register.status != "OPEN":
        raise HTTPException(
            status_code=409,
            detail={"code": "CASH_REGISTER_ALREADY_CLOSED", "message": "La caja ya está cerrada."},
        )

    from .cash_service import CashService

    closed_at = datetime.now()
    summary = CashService._summary(db, register, counted_cash)
    register.expected_cash = summary["expected_cash"]
    register.counted_cash = counted_cash
    register.difference = summary["difference"]
    register.closing_notes = closing_notes
    register.closed_at = closed_at
    register.closed_by = _actor_name(current_user)
    register.status = "CLOSED"
    register.updated_at = closed_at
    db.flush()
    return register


def close_branch(
    db: Session, tenant_id: int, branch_id: int, current_user: object
) -> CashDayBranchDB:
    day = require_open_day(db, tenant_id)
    branch_day = db.scalar(
        select(CashDayBranchDB)
        .where(
            CashDayBranchDB.tenant_id == tenant_id,
            CashDayBranchDB.cash_day_id == day.id,
            CashDayBranchDB.branch_id == branch_id,
        )
        .with_for_update()
    )
    if branch_day is None:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada en el día operativo.")
    if branch_day.status != "OPEN":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CASH_BRANCH_ALREADY_CLOSED",
                "message": "La sucursal ya está cerrada.",
            },
        )

    open_register_id = db.scalar(
        select(CashRegisterDB.id)
        .where(
            CashRegisterDB.tenant_id == tenant_id,
            CashRegisterDB.cash_day_id == day.id,
            CashRegisterDB.branch_id == branch_id,
            CashRegisterDB.status == "OPEN",
        )
        .limit(1)
    )
    if open_register_id is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CASH_BRANCH_HAS_OPEN_BOXES",
                "message": "No se puede cerrar la sucursal porque todavía tiene cajas abiertas.",
            },
        )

    now = datetime.now()
    branch_day.status = "CLOSED"
    branch_day.closed_at = now
    branch_day.closed_by = _actor_name(current_user)
    branch_day.updated_at = now
    db.flush()
    return branch_day


def close_day(db: Session, tenant_id: int, current_user: object) -> CashDayDB:
    day = require_open_day(db, tenant_id)
    open_branch_id = db.scalar(
        select(CashDayBranchDB.id)
        .where(
            CashDayBranchDB.tenant_id == tenant_id,
            CashDayBranchDB.cash_day_id == day.id,
            CashDayBranchDB.status == "OPEN",
        )
        .limit(1)
    )
    if open_branch_id is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CASH_DAY_HAS_OPEN_BRANCHES",
                "message": "No se puede cerrar el día porque todavía hay sucursales abiertas.",
            },
        )

    open_register_id = db.scalar(
        select(CashRegisterDB.id)
        .where(
            CashRegisterDB.tenant_id == tenant_id,
            CashRegisterDB.cash_day_id == day.id,
            CashRegisterDB.status == "OPEN",
        )
        .limit(1)
    )
    if open_register_id is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CASH_DAY_HAS_OPEN_BOXES",
                "message": "No se puede cerrar el día porque todavía hay cajas abiertas.",
            },
        )

    now = datetime.now()
    day.status = "CLOSED"
    day.closed_at = now
    day.closed_by = _actor_name(current_user)
    day.updated_at = now
    db.flush()
    return day


def serialize_day(db: Session, day: CashDayDB) -> dict:
    branch_rows = db.scalars(
        select(CashDayBranchDB)
        .where(CashDayBranchDB.tenant_id == day.tenant_id, CashDayBranchDB.cash_day_id == day.id)
        .options(joinedload(CashDayBranchDB.branch))
        .order_by(CashDayBranchDB.branch_id)
    ).all()
    registers = db.scalars(
        select(CashRegisterDB)
        .where(CashRegisterDB.tenant_id == day.tenant_id, CashRegisterDB.cash_day_id == day.id)
        .order_by(CashRegisterDB.branch_id, CashRegisterDB.id)
    ).all()
    box_rows = db.execute(
        select(CashBoxDB.id, CashBoxDB.name, CashBoxDB.base_amount)
        .where(CashBoxDB.tenant_id == day.tenant_id)
    ).all()
    box_names = {box_id: name for box_id, name, _base in box_rows}
    box_bases = {box_id: base for box_id, _name, base in box_rows}
    branch_names = {
        branch.id: branch.name
        for branch in db.scalars(select(BranchDB).where(BranchDB.tenant_id == day.tenant_id)).all()
    }
    return {
        "id": day.id,
        "tenant_id": day.tenant_id,
        "business_date": day.business_date,
        "status": day.status,
        "opened_at": day.opened_at,
        "opened_by": day.opened_by,
        "closed_at": day.closed_at,
        "closed_by": day.closed_by,
        "closing_notes": day.closing_notes,
        "branches": [
            {
                "id": row.id,
                "branch_id": row.branch_id,
                "branch_name": row.branch.name,
                "status": row.status,
                "opened_at": row.opened_at,
                "closed_at": row.closed_at,
                "closed_by": row.closed_by,
            }
            for row in branch_rows
        ],
        "registers": [
            {
                "id": register.id,
                "branch_id": register.branch_id,
                "branch_name": branch_names.get(register.branch_id),
                "cash_box_id": register.cash_box_id,
                "cash_box_name": box_names.get(register.cash_box_id),
                "base_amount": box_bases.get(register.cash_box_id, register.opening_amount),
                "opening_amount": register.opening_amount,
                "status": register.status,
                "expected_cash": register.expected_cash,
                "counted_cash": register.counted_cash,
                "difference": register.difference,
                "opened_at": register.opened_at,
                "closed_at": register.closed_at,
                "closed_by": register.closed_by,
            }
            for register in registers
        ],
    }
