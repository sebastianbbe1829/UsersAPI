from sqlalchemy.orm import Session

from ..models import ExtinguisherInspectionItemDB


class ExtinguisherInspectionItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, include_inactive: bool = True):
        query = self.db.query(ExtinguisherInspectionItemDB)
        if not include_inactive:
            query = query.filter(ExtinguisherInspectionItemDB.active.is_(True))
        return query.order_by(
            ExtinguisherInspectionItemDB.display_order,
            ExtinguisherInspectionItemDB.id,
        ).all()

    def get_by_id(self, item_id: int, include_inactive: bool = True):
        query = self.db.query(ExtinguisherInspectionItemDB).filter(
            ExtinguisherInspectionItemDB.id == item_id
        )
        if not include_inactive:
            query = query.filter(ExtinguisherInspectionItemDB.active.is_(True))
        return query.first()

    def get_by_code(self, code: str):
        return (
            self.db.query(ExtinguisherInspectionItemDB)
            .filter(ExtinguisherInspectionItemDB.code == code)
            .first()
        )

    def add(self, item: ExtinguisherInspectionItemDB):
        self.db.add(item)
        self.db.flush()
        return item

    def update(self, item: ExtinguisherInspectionItemDB):
        self.db.add(item)
        self.db.flush()
        return item
