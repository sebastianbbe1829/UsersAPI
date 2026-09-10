from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from ..models import InventoryMovementDB


class InventoryMovementRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, movement: InventoryMovementDB) -> InventoryMovementDB:
        self.db.add(movement)
        self.db.flush()
        return movement

    def get_by_id(self, tenant_id: int, movement_id: UUID) -> InventoryMovementDB | None:
        return (
            self.db.query(InventoryMovementDB)
            .filter(
                InventoryMovementDB.tenant_id == tenant_id,
                InventoryMovementDB.id == movement_id,
            )
            .first()
        )

    def list_by_product(
        self,
        tenant_id: int,
        product_id: int,
        limit: int | None = None,
        offset: int = 0,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[InventoryMovementDB]:
        query = self._base_query(tenant_id).filter(
            InventoryMovementDB.product_id == product_id,
        )
        query = self._apply_dates(query, from_date, to_date)
        query = query.order_by(
            InventoryMovementDB.business_date.desc(),
            InventoryMovementDB.created_at.desc(),
            InventoryMovementDB.id.desc(),
        ).offset(max(offset, 0))
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def list_all(
        self,
        tenant_id: int,
        limit: int | None = None,
        offset: int = 0,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[InventoryMovementDB]:
        query = self._base_query(tenant_id)
        query = self._apply_dates(query, from_date, to_date)
        query = query.order_by(
            InventoryMovementDB.business_date.desc(),
            InventoryMovementDB.created_at.desc(),
            InventoryMovementDB.id.desc(),
        ).offset(max(offset, 0))
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def _base_query(self, tenant_id: int):
        return self.db.query(InventoryMovementDB).filter(
            InventoryMovementDB.tenant_id == tenant_id,
        )

    @staticmethod
    def _apply_dates(
        query,
        from_date: date | None,
        to_date: date | None,
    ):
        if from_date is not None:
            query = query.filter(InventoryMovementDB.business_date >= from_date)
        if to_date is not None:
            query = query.filter(InventoryMovementDB.business_date <= to_date)
        return query
