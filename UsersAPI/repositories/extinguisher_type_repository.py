from sqlalchemy.orm import Session

from ..models import ExtinguisherTypeDB


class ExtinguisherTypeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, include_inactive: bool = False) -> list[ExtinguisherTypeDB]:
        query = self.db.query(ExtinguisherTypeDB)
        if not include_inactive:
            query = query.filter(ExtinguisherTypeDB.active.is_(True))
        return query.order_by(ExtinguisherTypeDB.name).all()

    def get_by_id(self, type_id: int, include_inactive: bool = False) -> ExtinguisherTypeDB | None:
        query = self.db.query(ExtinguisherTypeDB).filter(ExtinguisherTypeDB.id == type_id)
        if not include_inactive:
            query = query.filter(ExtinguisherTypeDB.active.is_(True))
        return query.first()

    def get_by_code(self, code: str) -> ExtinguisherTypeDB | None:
        return self.db.query(ExtinguisherTypeDB).filter(ExtinguisherTypeDB.code == code).first()

    def add(self, item: ExtinguisherTypeDB) -> ExtinguisherTypeDB:
        self.db.add(item)
        self.db.flush()
        return item
