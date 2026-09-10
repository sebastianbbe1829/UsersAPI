from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..models import SaleDraftDB
from ..schemas import SaleDraftCreate


def _actor_name(current_user: object | None) -> str:
    return (
        getattr(current_user, "email", None) or getattr(current_user, "username", None) or "system"
    )


def _next_draft_number(db: Session, tenant_id: int) -> str:
    db.execute(
        text("SELECT pg_advisory_xact_lock(:tenant_id, 7102)"),
        {"tenant_id": tenant_id},
    )
    last_number = db.execute(
        text(
            """
            SELECT COALESCE(
                MAX(CAST(SUBSTRING(draft_number FROM '^PV-([0-9]+)$') AS BIGINT)),
                0
            )
            FROM users_api.sale_drafts
            WHERE tenant_id = :tenant_id
              AND draft_number ~ '^PV-[0-9]+$'
            """
        ),
        {"tenant_id": tenant_id},
    ).scalar_one()
    return f"PV-{int(last_number) + 1:06d}"


def create_draft(
    data: SaleDraftCreate,
    db: Session,
    tenant_id: int,
    current_user: object,
    is_autoconsumption: bool = False,
) -> SaleDraftDB:
    if is_autoconsumption and data.discount_percentage != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Autoconsumption drafts cannot apply additional discounts",
        )

    payload = data.model_dump(mode="json")
    payload["is_autoconsumption"] = is_autoconsumption
    draft = SaleDraftDB(
        tenant_id=tenant_id,
        draft_number=_next_draft_number(db, tenant_id),
        payload=payload,
        created_by=_actor_name(current_user),
    )
    db.add(draft)
    db.flush()
    return draft


def list_drafts(db: Session, tenant_id: int) -> list[SaleDraftDB]:
    return list(
        db.scalars(
            select(SaleDraftDB)
            .where(SaleDraftDB.tenant_id == tenant_id)
            .order_by(SaleDraftDB.updated_at.desc())
        )
    )


def get_draft(draft_id: UUID, db: Session, tenant_id: int) -> SaleDraftDB:
    draft = db.scalar(
        select(SaleDraftDB).where(
            SaleDraftDB.id == draft_id,
            SaleDraftDB.tenant_id == tenant_id,
        )
    )
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frozen sale not found",
        )
    return draft


def delete_draft(draft_id: UUID, db: Session, tenant_id: int) -> None:
    draft = get_draft(draft_id, db, tenant_id)
    db.delete(draft)
    db.flush()
