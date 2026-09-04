from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..models import ExtinguisherDB, ExtinguisherTypeDB


class ExtinguisherRepository:

    def __init__(self, db: Session):
        self.db = db

    def add(self, extinguisher: ExtinguisherDB) -> ExtinguisherDB:
        self.db.add(extinguisher)
        self.db.flush()
        return extinguisher

    def get_all_by_tenant(
        self,
        tenant_id: int,
        include_inactive: bool = False,
    ) -> list[ExtinguisherDB]:
        query = (
            self.db.query(ExtinguisherDB)
            .filter(ExtinguisherDB.tenant_id == tenant_id)
        )
        if not include_inactive:
            query = query.filter(ExtinguisherDB.active.is_(True))
        return query.order_by(
            ExtinguisherDB.next_recharge_date.asc().nullslast(),
            ExtinguisherDB.id.asc(),
        ).all()

    def search_by_tenant(
        self,
        tenant_id: int,
        search: str,
        limit: int = 20,
    ) -> list[ExtinguisherDB]:
        texto = search.strip()
        query = (
            self.db.query(ExtinguisherDB)
            .options(joinedload(ExtinguisherDB.extinguisher_type))
            .filter(
                ExtinguisherDB.tenant_id == tenant_id,
                ExtinguisherDB.active.is_(True),
            )
        )
        if texto:
            patron = f"%{texto}%"
            query = query.filter(
                or_(
                    ExtinguisherDB.code.ilike(patron),
                    ExtinguisherDB.location.ilike(patron),
                    ExtinguisherDB.capacity.ilike(patron),
                    ExtinguisherDB.extinguisher_type.has(
                        ExtinguisherTypeDB.name.ilike(patron)
                    ),
                )
            )
        return query.order_by(
            ExtinguisherDB.code.asc(),
            ExtinguisherDB.id.asc(),
        ).limit(limit).all()

    def get_by_id_and_tenant(
        self,
        extinguisher_id: int,
        tenant_id: int,
        include_inactive: bool = False,
    ) -> ExtinguisherDB | None:
        query = (
            self.db.query(ExtinguisherDB)
            .filter(
                ExtinguisherDB.id == extinguisher_id,
                ExtinguisherDB.tenant_id == tenant_id,
            )
        )
        if not include_inactive:
            query = query.filter(ExtinguisherDB.active.is_(True))
        return query.first()

    def get_by_code_and_tenant(
        self,
        code: str,
        tenant_id: int,
        include_inactive: bool = False,
    ) -> ExtinguisherDB | None:
        query = (
            self.db.query(ExtinguisherDB)
            .filter(
                ExtinguisherDB.code == code,
                ExtinguisherDB.tenant_id == tenant_id,
            )
        )
        if not include_inactive:
            query = query.filter(ExtinguisherDB.active.is_(True))
        return query.first()

    def update(self, extinguisher: ExtinguisherDB) -> ExtinguisherDB:
        self.db.add(extinguisher)
        self.db.flush()
        return extinguisher
