from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models import UserCashAssignmentDB


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
        }

    from ..models import CashRegisterDB

    register = db.scalar(
        select(CashRegisterDB)
        .where(
            CashRegisterDB.tenant_id == tenant_id,
            CashRegisterDB.cash_box_id == assignment.cash_box_id,
            CashRegisterDB.status == "OPEN",
        )
        .order_by(CashRegisterDB.id.desc())
    )

    return {
        "assigned": True,
        "tenant_id": tenant_id,
        "branch_id": assignment.branch_id,
        "branch_name": assignment.branch.name,
        "cash_box_id": assignment.cash_box_id,
        "cash_box_name": assignment.cash_box.name,
        "cash_box_status": "ACTIVE" if assignment.cash_box.status == 1 else "INACTIVE",
        "register_id": register.id if register else None,
        "register_status": register.status if register else "CLOSED",
        "business_date": register.business_date if register else None,
    }
