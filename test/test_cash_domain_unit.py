from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from UsersAPI.domains.cash.models import CashMovementDB
from UsersAPI.domains.cash.services import cash_movement_service
from UsersAPI.domains.cash.services.cash_service import _payment_bucket, _signed_amount


def user():
    return SimpleNamespace(email="cash@test.local")


def test_payment_bucket_normalizes_supported_methods():
    assert _payment_bucket("EFECTIVO") == "cash"
    assert _payment_bucket("TARJETA") == "card"
    assert _payment_bucket("TRANSFERENCIA") == "transfer"
    assert _payment_bucket("CREDITO") == "credit"


def test_signed_amount_respects_movement_type():
    income = SimpleNamespace(amount=Decimal("100"), movement_type="INCOME")
    expense = SimpleNamespace(amount=Decimal("40"), movement_type="EXPENSE")

    assert _signed_amount(income) == Decimal("100")
    assert _signed_amount(expense) == Decimal("-40")


def test_automatic_movement_requires_open_register(monkeypatch):
    monkeypatch.setattr(cash_movement_service.CashRepository, "get_open", lambda *_: None)

    with pytest.raises(HTTPException) as error:
        cash_movement_service.record_automatic_movement(
            MagicMock(), 7, Decimal("100"), "EFECTIVO", "SALE", uuid4(), "Venta", user()
        )

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "USER_CASH_REGISTER_CLOSED"
    assert "caja" in error.value.detail["message"].lower()


def test_automatic_movement_is_transactional_and_keeps_origin(monkeypatch):
    register = SimpleNamespace(id=12)
    db = MagicMock()
    monkeypatch.setattr(cash_movement_service.CashRepository, "get_open", lambda *_: register)

    movement = cash_movement_service.record_automatic_movement(
        db, 7, Decimal("100.00"), "TARJETA", "SALE", uuid4(), "Venta VTA-1", user()
    )

    assert isinstance(movement, CashMovementDB)
    assert movement.tenant_id == 7
    assert movement.cash_register_id == 12
    assert movement.movement_type == "INCOME"
    assert movement.payment_method == "TARJETA"
    assert movement.origin_type == "SALE"
    assert movement.description == "Venta VTA-1"
    db.add.assert_called_once_with(movement)
    db.flush.assert_called_once()


def test_payment_reversal_is_expense_in_current_register(monkeypatch):
    register = SimpleNamespace(id=15)
    db = MagicMock()
    monkeypatch.setattr(cash_movement_service.CashRepository, "get_open", lambda *_: register)
    payment_id = uuid4()

    movement = cash_movement_service.record_payment_reversal(
        db, 7, Decimal("80.00"), "EFECTIVO", payment_id, user()
    )

    assert movement.cash_register_id == 15
    assert movement.movement_type == "EXPENSE"
    assert movement.payment_method == "EFECTIVO"
    assert movement.origin_type == "PAYMENT_REVERSAL"
    assert movement.origin_id == str(payment_id)
