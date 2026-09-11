from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models import (
    CashDayBranchDB,
    CashDayDB,
    CashRegisterDB,
    UserCashAssignmentDB,
)


def _base_context(tenant_id: int) -> dict:
    return {
        "assigned": False,
        "tenant_id": tenant_id,
        "branch_id": None,
        "branch_name": None,
        "cash_box_id": None,
        "cash_box_name": None,
        "cash_box_status": None,
        "register_id": None,
        "register_status": None,
        "business_date": None,
        "day_id": None,
        "day_status": None,
        "branch_day_status": None,
        "operational": False,
        "blocked_reason": "USER_CASH_REGISTER_NOT_ASSIGNED",
    }


def get_user_cash_context(db: Session, tenant_id: int, user_tenant_id: int) -> dict:
    assignment = db.scalar(
        select(UserCashAssignmentDB)
        .where(
            UserCashAssignmentDB.tenant_id == tenant_id,
            UserCashAssignmentDB.user_tenant_id == user_tenant_id,
            UserCashAssignmentDB.status == 1,
        )
        .options(
            joinedload(UserCashAssignmentDB.branch),
            joinedload(UserCashAssignmentDB.cash_box),
        )
    )

    if assignment is None:
        return _base_context(tenant_id)

    context = _base_context(tenant_id)
    context.update(
        {
            "assigned": True,
            "branch_id": assignment.branch_id,
            "branch_name": assignment.branch.name,
            "cash_box_id": assignment.cash_box_id,
            "cash_box_name": assignment.cash_box.name,
            "cash_box_status": "ACTIVE" if assignment.cash_box.status == 1 else "INACTIVE",
            "blocked_reason": None,
        }
    )

    if assignment.branch.status != 1:
        context["blocked_reason"] = "CASH_BRANCH_INACTIVE"
        return context
    if assignment.cash_box.status != 1:
        context["blocked_reason"] = "CASH_BOX_INACTIVE"
        return context

    day = db.scalar(
        select(CashDayDB)
        .where(
            CashDayDB.tenant_id == tenant_id,
            CashDayDB.status == "OPEN",
        )
        .order_by(CashDayDB.business_date.desc(), CashDayDB.id.desc())
    )
    if day is None:
        context["blocked_reason"] = "CASH_DAY_NOT_STARTED"
        return context

    context.update(
        {
            "day_id": day.id,
            "day_status": day.status,
            "business_date": day.business_date,
        }
    )

    branch_day = db.scalar(
        select(CashDayBranchDB).where(
            CashDayBranchDB.tenant_id == tenant_id,
            CashDayBranchDB.cash_day_id == day.id,
            CashDayBranchDB.branch_id == assignment.branch_id,
        )
    )
    context["branch_day_status"] = branch_day.status if branch_day else None
    if branch_day is None or branch_day.status != "OPEN":
        context["blocked_reason"] = "CASH_BRANCH_CLOSED"
        return context

    register = db.scalar(
        select(CashRegisterDB)
        .where(
            CashRegisterDB.tenant_id == tenant_id,
            CashRegisterDB.cash_day_id == day.id,
            CashRegisterDB.cash_box_id == assignment.cash_box_id,
        )
        .order_by(CashRegisterDB.id.desc())
    )
    if register is None:
        context["blocked_reason"] = "CASH_REGISTER_NOT_STARTED"
        return context

    context.update({"register_id": register.id, "register_status": register.status})
    if register.status != "OPEN":
        context["blocked_reason"] = "CASH_REGISTER_CLOSED"
        return context

    context["operational"] = True
    context["blocked_reason"] = None
    return context


def require_operational_context(db: Session, tenant_id: int, current_user: object) -> dict:
    context = get_user_cash_context(
        db,
        tenant_id,
        int(getattr(current_user, "id", 0)),
    )
    if not context["operational"]:
        code = context["blocked_reason"] or "CASH_CONTEXT_BLOCKED"
        messages = {
            "USER_CASH_REGISTER_NOT_ASSIGNED": (
                "El usuario no está asignado a ninguna sucursal y caja."
            ),
            "CASH_BRANCH_INACTIVE": "La sucursal asignada está inactiva.",
            "CASH_BOX_INACTIVE": "La caja asignada está inactiva.",
            "CASH_DAY_NOT_STARTED": (
                "No existe una caja abierta. No es posible realizar ventas ni pagos."
            ),
            "CASH_DAY_CLOSED": (
                "No existe una caja abierta. No es posible realizar ventas ni pagos."
            ),
            "CASH_BRANCH_CLOSED": "La sucursal asignada está cerrada.",
            "CASH_REGISTER_NOT_STARTED": (
                "La caja asignada no tiene sesión para el día operativo."
            ),
            "CASH_REGISTER_CLOSED": "La caja asignada está cerrada.",
        }
        raise HTTPException(
            status_code=409,
            detail={
                "code": code,
                "message": messages.get(code, "La operación de caja no está habilitada."),
            },
        )
    return context
