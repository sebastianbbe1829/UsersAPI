from datetime import datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from ..models import UserCashAssignmentDB


def deactivate_user_cash_assignment(
    db: Session,
    tenant_id: int,
    user_tenant_id: int,
    reason: str = "user deletion",
) -> None:
    db.execute(
        update(UserCashAssignmentDB)
        .where(
            UserCashAssignmentDB.tenant_id == tenant_id,
            UserCashAssignmentDB.user_tenant_id == user_tenant_id,
            UserCashAssignmentDB.status == 1,
        )
        .values(
            status=0,
            unassigned_at=datetime.now(),
            unassigned_by=reason,
        )
    )
