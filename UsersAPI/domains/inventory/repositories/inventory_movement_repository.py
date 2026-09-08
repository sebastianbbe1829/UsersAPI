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
    ) -> list[InventoryMovementDB]:
        query = (
            self.db.query(InventoryMovementDB)
            .filter(
                InventoryMovementDB.tenant_id == tenant_id,
                InventoryMovementDB.product_id == product_id,
            )
            .order_by(InventoryMovementDB.created_at, InventoryMovementDB.id)
            .offset(max(offset, 0))
        )
        if limit is not None:
            query = query.limit(limit)
        return query.all()
