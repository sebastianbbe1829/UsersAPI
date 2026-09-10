from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import CashMovementDB, CashRegisterDB


class CashRepository:
    @staticmethod
    def get_open(
        db: Session, tenant_id: int, cash_box_id: int | None = None
    ) -> CashRegisterDB | None:
        query = select(CashRegisterDB).where(
            CashRegisterDB.tenant_id == tenant_id,
            CashRegisterDB.status == "OPEN",
        )
        if cash_box_id is not None:
            query = query.where(CashRegisterDB.cash_box_id == cash_box_id)
        return db.scalar(query.options(selectinload(CashRegisterDB.movements)))

    @staticmethod
    def get(db: Session, tenant_id: int, register_id: int) -> CashRegisterDB | None:
        return db.scalar(
            select(CashRegisterDB)
            .where(
                CashRegisterDB.tenant_id == tenant_id,
                CashRegisterDB.id == register_id,
            )
            .options(selectinload(CashRegisterDB.movements))
        )

    @staticmethod
    def list_all(
        db: Session, tenant_id: int, limit: int, offset: int
    ) -> list[CashRegisterDB]:
        return list(
            db.scalars(
                select(CashRegisterDB)
                .where(CashRegisterDB.tenant_id == tenant_id)
                .order_by(CashRegisterDB.id.desc())
                .offset(offset)
                .limit(limit)
                .options(selectinload(CashRegisterDB.movements))
            ).all()
        )

    @staticmethod
    def add_register(db: Session, register: CashRegisterDB) -> CashRegisterDB:
        db.add(register)
        db.flush()
        return register

    @staticmethod
    def add_movement(db: Session, movement: CashMovementDB) -> CashMovementDB:
        db.add(movement)
        db.flush()
        return movement
