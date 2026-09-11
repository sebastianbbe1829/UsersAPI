from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from UsersAPI.domains.sales.models import SaleDB, SalePaymentDB

from ..models import CashMovementDB, CashRegisterDB, UserCashAssignmentDB
from ..repositories import CashRepository
from ..schemas import CashMovementCreate, CashRegisterClose, CashRegisterOpen
from .cash_context_service import require_operational_context

ZERO = Decimal("0.00")
CASH_METHODS = {"CASH", "EFECTIVO"}


def _user_name(current_user) -> str:
    return str(
        getattr(current_user, "email", None)
        or getattr(current_user, "username", None)
        or getattr(current_user, "id", "system")
    )[:100]


def _assignment(db: Session, tenant_id: int, current_user) -> UserCashAssignmentDB:
    assignment = db.scalar(
        select(UserCashAssignmentDB).where(
            UserCashAssignmentDB.tenant_id == tenant_id,
            UserCashAssignmentDB.user_tenant_id == getattr(current_user, "id", None),
            UserCashAssignmentDB.status == 1,
        )
    )
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "USER_CASH_REGISTER_NOT_ASSIGNED",
                "message": "El usuario no está asignado a ninguna sucursal y caja.",
            },
        )
    return assignment


def _is_cash(payment_method: str | None) -> bool:
    return (payment_method or "").strip().upper() in CASH_METHODS


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


def _signed_amount(movement: CashMovementDB) -> Decimal:
    amount = Decimal(str(movement.amount or 0))
    return amount if movement.movement_type == "INCOME" else -amount


class CashService:
    @staticmethod
    def open_register(
        data: CashRegisterOpen, db: Session, tenant_id: int, current_user
    ) -> CashRegisterDB:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CASH_REGISTER_OPENING_DISABLED",
                "message": "Las cajas se abren al iniciar el día operativo.",
            },
        )

    @staticmethod
    def get_current(db: Session, tenant_id: int, current_user=None) -> CashRegisterDB:
        if current_user is not None:
            assignment = _assignment(db, tenant_id, current_user)
            register = CashRepository.get_open(db, tenant_id, assignment.cash_box_id)
        else:
            register = CashRepository.get_open(db, tenant_id)
        if not register:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe una caja abierta para el contexto del usuario.",
            )
        return register

    @staticmethod
    def get_register(db: Session, tenant_id: int, register_id: int) -> CashRegisterDB:
        register = CashRepository.get(db, tenant_id, register_id)
        if not register:
            raise HTTPException(status_code=404, detail="Caja no encontrada.")
        return register

    @staticmethod
    def list_registers(
        db: Session, tenant_id: int, limit: int, offset: int
    ) -> list[CashRegisterDB]:
        return CashRepository.list_all(db, tenant_id, limit=limit, offset=offset)

    @staticmethod
    def add_movement(
        data: CashMovementCreate,
        db: Session,
        tenant_id: int,
        register_id: int,
        current_user,
    ) -> CashMovementDB:
        context = require_operational_context(db, tenant_id, current_user)
        if context["register_id"] != register_id:
            raise HTTPException(
                status_code=403,
                detail="La caja indicada no corresponde a la caja asignada al usuario.",
            )
        register = CashService.get_register(db, tenant_id, register_id)
        if register.status != "OPEN":
            raise HTTPException(
                status_code=409,
                detail="No se pueden registrar movimientos en una caja cerrada.",
            )
        movement_type = data.movement_type.strip().upper()
        if movement_type not in {"INCOME", "EXPENSE"}:
            raise HTTPException(
                status_code=422,
                detail="movement_type debe ser INCOME o EXPENSE.",
            )
        movement = CashMovementDB(
            tenant_id=tenant_id,
            cash_register_id=register_id,
            business_date=context["business_date"],
            movement_type=movement_type,
            amount=data.amount,
            payment_method="EFECTIVO",
            origin_type="MANUAL",
            description=data.description,
            created_by=_user_name(current_user),
        )
        return CashRepository.add_movement(db, movement)

    @staticmethod
    def _summary(
        db: Session,
        register: CashRegisterDB,
        counted_cash: Decimal | None = None,
    ) -> dict:
        movements = db.scalars(
            select(CashMovementDB).where(
                CashMovementDB.tenant_id == register.tenant_id,
                CashMovementDB.cash_register_id == register.id,
                CashMovementDB.business_date == register.business_date,
            )
        ).all()
        sales = {"cash": ZERO, "transfer": ZERO, "card": ZERO}
        portfolio_cash = ZERO
        manual_income = ZERO
        manual_expense = ZERO
        physical_cash_delta = ZERO
        for movement in movements:
            signed = _signed_amount(movement)
            bucket = _payment_bucket(movement.payment_method)
            if movement.origin_type == "SALE" and bucket in sales:
                sales[bucket] += signed
            elif movement.origin_type in {
                "PORTFOLIO_PAYMENT",
                "PAYMENT_REVERSAL",
            } and _is_cash(movement.payment_method):
                portfolio_cash += signed
            elif movement.origin_type == "MANUAL":
                if movement.movement_type == "INCOME":
                    manual_income += Decimal(str(movement.amount or 0))
                else:
                    manual_expense += Decimal(str(movement.amount or 0))
            if _is_cash(movement.payment_method):
                physical_cash_delta += signed
        sales_credit = db.scalar(
            select(func.coalesce(func.sum(SalePaymentDB.amount), 0))
            .join(SaleDB, SaleDB.id == SalePaymentDB.sale_id)
            .where(
                SalePaymentDB.tenant_id == register.tenant_id,
                SalePaymentDB.payment_method.in_(["CREDITO", "CREDIT", "CRÉDITO"]),
                SaleDB.business_date == register.business_date,
            )
        )
        expected_cash = Decimal(str(register.opening_amount or 0)) + physical_cash_delta
        return {
            "sales_cash": sales["cash"],
            "sales_transfer": sales["transfer"],
            "sales_card": sales["card"],
            "sales_credit": Decimal(str(sales_credit or 0)),
            "portfolio_cash": portfolio_cash,
            "manual_income": manual_income,
            "manual_expense": manual_expense,
            "expected_cash": expected_cash,
            "counted_cash": counted_cash,
            "difference": (None if counted_cash is None else counted_cash - expected_cash),
        }

    @staticmethod
    def close_register(
        data: CashRegisterClose,
        db: Session,
        tenant_id: int,
        register_id: int,
        current_user,
    ) -> CashRegisterDB:
        assignment = _assignment(db, tenant_id, current_user)
        register = CashService.get_register(db, tenant_id, register_id)
        if register.cash_box_id != assignment.cash_box_id:
            raise HTTPException(
                status_code=403,
                detail="La caja no corresponde al usuario asignado.",
            )
        if register.status != "OPEN":
            raise HTTPException(
                status_code=409,
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
        return CashService._summary(db, register, register.counted_cash)
