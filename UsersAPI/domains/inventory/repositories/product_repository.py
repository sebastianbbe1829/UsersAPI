from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ..models import InventoryMovementDB, ProductDB


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, product: ProductDB) -> ProductDB:
        self.db.add(product)
        self.db.flush()
        return product

    def get_by_id(self, tenant_id: int, product_id: int) -> ProductDB | None:
        return (
            self.db.query(ProductDB)
            .filter(
                ProductDB.tenant_id == tenant_id,
                ProductDB.id == product_id,
            )
            .first()
        )

    def get_by_code(self, tenant_id: int, code: str) -> ProductDB | None:
        return (
            self.db.query(ProductDB)
            .filter(
                ProductDB.tenant_id == tenant_id,
                ProductDB.code == code,
            )
            .first()
        )

    def next_code(self, tenant_id: int) -> str:
        # Serialize code generation for this tenant inside the current transaction.
        self.db.execute(
            text("SELECT pg_advisory_xact_lock(:tenant_id)"),
            {"tenant_id": tenant_id},
        )
        last_number = self.db.execute(
            text(
                """
                SELECT COALESCE(
                    MAX(CAST(SUBSTRING(code FROM '^PROD-([0-9]+)$') AS BIGINT)),
                    0
                )
                FROM users_api.products
                WHERE tenant_id = :tenant_id
                  AND code ~ '^PROD-[0-9]+$'
                """
            ),
            {"tenant_id": tenant_id},
        ).scalar_one()
        return f"PROD-{int(last_number) + 1:06d}"

    def list(self, tenant_id: int, active_only: bool = False) -> list[ProductDB]:
        query = self.db.query(ProductDB).filter(ProductDB.tenant_id == tenant_id)
        if active_only:
            query = query.filter(ProductDB.active.is_(True))
        return query.order_by(ProductDB.name, ProductDB.id).all()

    def list_top_selling(
        self,
        tenant_id: int,
        limit: int = 6,
    ) -> list[ProductDB]:
        sales_quantity = func.coalesce(func.sum(InventoryMovementDB.quantity), 0)
        return (
            self.db.query(ProductDB)
            .join(
                InventoryMovementDB,
                (InventoryMovementDB.tenant_id == ProductDB.tenant_id)
                & (InventoryMovementDB.product_id == ProductDB.id),
            )
            .filter(
                ProductDB.tenant_id == tenant_id,
                ProductDB.active.is_(True),
                InventoryMovementDB.origin_type == "SALE",
                InventoryMovementDB.movement_type == "EXIT",
            )
            .group_by(ProductDB.id)
            .order_by(sales_quantity.desc(), ProductDB.name, ProductDB.id)
            .limit(limit)
            .all()
        )

    def save(self, product: ProductDB) -> ProductDB:
        self.db.add(product)
        self.db.flush()
        return product
