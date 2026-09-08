from sqlalchemy.orm import Session

from ..models import InventoryDB


class InventoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_product(
        self,
        tenant_id: int,
        product_id: int,
        lock: bool = False,
    ) -> InventoryDB | None:
        query = self.db.query(InventoryDB).filter(
            InventoryDB.tenant_id == tenant_id,
            InventoryDB.product_id == product_id,
        )
        if lock:
            query = query.with_for_update()
        return query.first()

    def list(self, tenant_id: int) -> list[InventoryDB]:
        return (
            self.db.query(InventoryDB)
            .filter(InventoryDB.tenant_id == tenant_id)
            .order_by(InventoryDB.product_id)
            .all()
        )

    def add(self, inventory: InventoryDB) -> InventoryDB:
        self.db.add(inventory)
        self.db.flush()
        return inventory

    def save(self, inventory: InventoryDB) -> InventoryDB:
        self.db.add(inventory)
        self.db.flush()
        return inventory
