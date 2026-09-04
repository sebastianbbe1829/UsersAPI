from sqlalchemy.orm import Session, joinedload

from ..models import (
    ExtinguisherDB,
    ExtinguisherInspectionDB,
    ExtinguisherInspectionItemDB,
    ExtinguisherInspectionResultDB,
)


class ExtinguisherInspectionItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_active(self):
        return (
            self.db.query(ExtinguisherInspectionItemDB)
            .filter(ExtinguisherInspectionItemDB.active.is_(True))
            .order_by(
                ExtinguisherInspectionItemDB.display_order,
                ExtinguisherInspectionItemDB.id,
            )
            .all()
        )

    def get_by_id(self, item_id: int):
        return (
            self.db.query(ExtinguisherInspectionItemDB)
            .filter(ExtinguisherInspectionItemDB.id == item_id)
            .first()
        )


class ExtinguisherInspectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_extinguisher_for_update(self, extinguisher_id: int, tenant_id: int):
        return (
            self.db.query(ExtinguisherDB)
            .filter(
                ExtinguisherDB.id == extinguisher_id,
                ExtinguisherDB.tenant_id == tenant_id,
                ExtinguisherDB.active.is_(True),
            )
            .with_for_update()
            .first()
        )

    def get_by_id_and_tenant(self, inspection_id: int, tenant_id: int):
        return (
            self.db.query(ExtinguisherInspectionDB)
            .options(
                joinedload(ExtinguisherInspectionDB.results).joinedload(
                    ExtinguisherInspectionResultDB.inspection_item
                )
            )
            .filter(
                ExtinguisherInspectionDB.id == inspection_id,
                ExtinguisherInspectionDB.tenant_id == tenant_id,
            )
            .first()
        )

    def get_all_by_tenant(self, tenant_id: int, extinguisher_id: int | None = None):
        query = (
            self.db.query(ExtinguisherInspectionDB)
            .options(
                joinedload(ExtinguisherInspectionDB.results).joinedload(
                    ExtinguisherInspectionResultDB.inspection_item
                )
            )
            .filter(ExtinguisherInspectionDB.tenant_id == tenant_id)
        )
        if extinguisher_id is not None:
            query = query.filter(ExtinguisherInspectionDB.extinguisher_id == extinguisher_id)
        return (
            query.order_by(
                ExtinguisherInspectionDB.inspection_date.desc(),
                ExtinguisherInspectionDB.id.desc(),
            )
            .all()
        )

    def add(self, inspection: ExtinguisherInspectionDB):
        self.db.add(inspection)
        self.db.flush()
        return inspection
