from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session, joinedload

from ..models import SaleDB


class SaleRepository:
    def __init__(self, db: Session):
        self.db = db

    def next_sale_number(self, tenant_id: int) -> str:
        self.db.execute(
            text("SELECT pg_advisory_xact_lock(:tenant_id, 7101)"),
            {"tenant_id": tenant_id},
        )
        last_number = self.db.execute(
            text(
                """
                SELECT COALESCE(
                    MAX(CAST(SUBSTRING(sale_number FROM '^VTA-([0-9]+)$') AS BIGINT)),
                    0
                )
                FROM users_api.sales
                WHERE tenant_id = :tenant_id
                  AND sale_number ~ '^VTA-[0-9]+$'
                """
            ),
            {"tenant_id": tenant_id},
        ).scalar_one()
        return f"VTA-{int(last_number) + 1:06d}"

    def add(self, sale: SaleDB) -> SaleDB:
        self.db.add(sale)
        return sale

    def get_by_id(self, tenant_id: int, sale_id: UUID) -> SaleDB | None:
        result = self.db.scalars(
            select(SaleDB)
            .options(
                joinedload(SaleDB.items),
                joinedload(SaleDB.customers),
                joinedload(SaleDB.payments),
            )
            .where(SaleDB.tenant_id == tenant_id, SaleDB.id == sale_id)
        ).unique()
        return result.first()

    def list(self, tenant_id: int, limit: int = 100, offset: int = 0) -> list[SaleDB]:
        return list(
            self.db.scalars(
                select(SaleDB)
                .options(
                    joinedload(SaleDB.items),
                    joinedload(SaleDB.customers),
                    joinedload(SaleDB.payments),
                )
                .where(SaleDB.tenant_id == tenant_id)
                .order_by(SaleDB.business_date.desc(), SaleDB.created_at.desc())
                .offset(offset)
                .limit(limit)
            ).unique()
        )
