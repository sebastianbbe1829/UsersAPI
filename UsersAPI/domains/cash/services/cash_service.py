from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from UsersAPI.domains.portfolio.models import PaymentDB
from UsersAPI.domains.sales.models import SaleDB, SalePaymentDB

from ..models import CashMovementDB, CashRegisterDB
from ..repositories import CashRepository
from ..schemas import CashMovementCreate, CashRegisterClose, CashRegisterOpen


ZERO = Decimal("0.00")


def _user_name(current_user) -> str:
    return str(
        getattr(current_user, "email", None)
        or getattr(current_user, "username", None)
        or getattr(current_user, "id", "system")
    )[:100]


def _is_cash(payment_method: str | None) -> bool:
    return (payment_method or "").strip().upper() in {"CASH", "EFECTIVO"}


def _payment_bucket(payment_method: str | None) -> str:
    method = (payment_method or "").strip().upper()
    if _is_cash(method):
        return "cash"
    if method in {"TRANSFER", "TRANSFERENCIA", "BANK_TRANSFER"}:
        return "transfer"
    if method in {"CARD", "TARJETA", "CREDIT_CARD", "DEBIT_CARD"}:
        return "card"
    if method in {"CREDIT", "CRÉDITO", "CREDITO"}:
        return "credit"
    return "other"


class CashService:
    @staticmethod
    def open_register(
        data: CashRegisterOpen,
        db: Session,
        tenant_id: int,
        current_user,
    ) -> CashRegisterDB:
        if CashRepository.get_open(db, tenant_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una caja abierta para el tenant.",
            )

        register = CashRegisterDB(
            tenant_id=tenant_id,
            opened_by=_user_name(current_user),
            opening_amount=data.opening_amount,
            status="OPEN",
        )
        return CashRepository.add_register(db, register)

    @staticmethod
    def get_current(db: Session, tenant_id: int) -> CashRegisterDB:
        register = CashRepository.get_open(db, tenant_id)
        if not register:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe una caja abierta para el tenant.",
            )
        return register

    @staticmethod
    def get_register(db: Session, tenant_id: int, register_id: int) -> CashRegisterDB:
        register = CashRepository.get(db, tenant_id, register_id)
        if not register:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Caja no encontrada.",
            )
        return register

    @staticmethod
    def list_registers(db: Session, tenant_id: int, limit: int, offset: int) -> list[CashRegisterDB]:
        return CashRepository.list_all(db, tenant_id, limit=limit, offset=offset)

    @staticmethod
    def add_movement(
        data: CashMovementCreate,
        db: Session,
        tenant_id: int,
        register_id: int,
        current_user,
    ) -> CashMovementDB:
        register = CashService.get_register(db, tenant_id, register_id)
        if register.status != "OPEN":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se pueden registrar movimientos en una caja cerrada.",
            )

        movement_type = data.movement_type.strip().upper()
        if movement_type not in {"INCOME", "EXPENSE"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="movement_type debe ser INCOME o EXPENSE.",
            )

        movement = CashMovementDB(
            tenant_id=tenant_id,
            cash_register_id=register_id,
            movement_type=movement_type,
            amount=data.amount,
            payment_method="EFECTIVO",
            origin_type="MANUAL",
            description=data.description,
            created_by=_user_name(current_user),
        )
        return CashRepository.add_movement(db, movement)

    @staticmethod
    def _summary(db: Session, register: CashRegisterDB, counted_cash: Decimal | None = None) -> dict:
        end_at = register.closed_at or datetime.now()

        sales_rows = db.execute(
            select(
                SalePaymentDB.payment_method,
                func.coalesce(func.sum(SalePaymentDB.amount), 0),
            )
            .join(SaleDB, SaleDB.id == SalePaymentDB.sale_id)
            .where(
                SalePaymentDB.tenant_id == register.tenant_id,
                SaleDB.status == "COMPLETED",
                SaleDB.created_at >= register.opened_at,
                SaleDB.created_at <= end_at,
            )
            .group_by(SalePaymentDB.payment_method)
        ).all()

        sales = {"cash": ZERO, "transfer": ZERO, "card": ZERO, "credit": ZERO}
        for method, amount in sales_rows:
            bucket = _payment_bucket(method)
            if bucket in sales:
                sales[bucket] += Decimal(str(amount))

        portfolio_cash = db.scalar(
            select(func.coalesce(func.sum(PaymentDB.amount), 0)).where(
                PaymentDB.tenant_id == register.tenant_id,
                PaymentDB.status == "APLICADO",
                PaymentDB.created_at >= register.opened_at,
                PaymentDB.created_at <= end_at,
                PaymentDB.payment_method.in_(["CASH", "EFECTIVO"]),
            )
        )
        portfolio_cash = Decimal(str(portfolio_cash or 0))

        manual_income = db.scalar(
            select(func.coalesce(func.sum(CashMovementDB.amount), 0)).where(
                CashMovementDB.tenant_id == register.tenant_id,
                CashMovementDB.cash_register_id == register.id,
                CashMovementDB.movement_type == "INCOME",
            )
        )
        manual_expense = db.scalar(
            select(func.coalesce(func.sum(CashMovementDB.amount), 0)).where(
                CashMovementDB.tenant_id == register.tenant_id,
                CashMovementDB.cash_register_id == register.id,
                CashMovementDB.movement_type == "EXPENSE",
            )
        )
        manual_income = Decimal(str(manual_income or 0))
        manual_expense = Decimal(str(manual_expense or 0))

        expected_cash = (
            Decimal(str(register.opening_amount or 0))
            + sales["cash"]
            + portfolio_cash
            + manual_income
            - manual_expense
        )
        difference = None if counted_cash is None else counted_cash - expected_cash

        return {
            "sales_cash": sales["cash"],
            "sales_transfer": sales["transfer"],
            "sales_card": sales["card"],
            "sales_credit": sales["credit"],
            "portfolio_cash": portfolio_cash,
            "manual_income": manual_income,
            "manual_expense": manual_expense,
            "expected_cash": expected_cash,
            "counted_cash": counted_cash,
            "difference": difference,
        }

    @staticmethod
    def close_register(
        data: CashRegisterClose,
        db: Session,
        tenant_id: int,
        register_id: int,
        current_user,
    ) -> CashRegisterDB:
        register = CashService.get_register(db, tenant_id, register_id)
        if register.status != "OPEN":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La caja ya está cerrada.",
            )

        register.closed_at = datetime.now()
        register.closed_by = _user_name(current_user)
        summary = CashService._summary(db, register, data.counted_cash)
        register.expected_cash = summary["expected_cash"]
        register.counted_cash = data.counted_cash
        register.difference = summary["difference"]
        register.closing_notes = data.closing_notes
        register.status = "CLOSED"
        register.updated_at = register.closed_at
        db.flush()
        return register

    @staticmethod
    def summary(db: Session, tenant_id: int, register_id: int) -> dict:
        register = CashService.get_register(db, tenant_id, register_id)
        counted = register.counted_cash
        return CashService._summary(db, register, counted)
