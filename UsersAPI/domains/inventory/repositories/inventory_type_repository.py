from sqlalchemy.orm import Session

from ..models import InventoryTypeDB


class InventoryTypeRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, inventory_type: InventoryTypeDB) -> InventoryTypeDB:
        self.db.add(inventory_type)
        self.db.flush()
        return inventory_type

    def get_by_id(self, tenant_id: int, inventory_type_id: int) -> InventoryTypeDB | None:
        return (
            self.db.query(InventoryTypeDB)
            .filter(
                InventoryTypeDB.tenant_id == tenant_id,
                InventoryTypeDB.id == inventory_type_id,
            )
            .first()
        )

    def get_by_code(self, tenant_id: int, code: str) -> InventoryTypeDB | None:
        return (
            self.db.query(InventoryTypeDB)
            .filter(
                InventoryTypeDB.tenant_id == tenant_id,
                InventoryTypeDB.code == code,
            )
            .first()
        )

    def list(self, tenant_id: int, active_only: bool = False) -> list[InventoryTypeDB]:
        query = self.db.query(InventoryTypeDB).filter(InventoryTypeDB.tenant_id == tenant_id)
        if active_only:
            query = query.filter(InventoryTypeDB.active.is_(True))
        return query.order_by(InventoryTypeDB.name, InventoryTypeDB.id).all()

    def save(self, inventory_type: InventoryTypeDB) -> InventoryTypeDB:
        self.db.add(inventory_type)
        self.db.flush()
        return inventory_type
