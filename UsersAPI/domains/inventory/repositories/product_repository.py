from sqlalchemy.orm import Session

from ..models import ProductDB


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

    def list(self, tenant_id: int, active_only: bool = False) -> list[ProductDB]:
        query = self.db.query(ProductDB).filter(ProductDB.tenant_id == tenant_id)
        if active_only:
            query = query.filter(ProductDB.active.is_(True))
        return query.order_by(ProductDB.name, ProductDB.id).all()

    def save(self, product: ProductDB) -> ProductDB:
        self.db.add(product)
        self.db.flush()
        return product
