from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from UsersAPI.domains.cash.services import cash_context_service, cash_day_service


def test_require_open_day_rejects_missing_day(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(cash_day_service, "get_current_day", lambda *_: None)

    with pytest.raises(HTTPException) as error:
        cash_day_service.require_open_day(db, 7)

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "CASH_DAY_NOT_STARTED"


def test_require_operational_context_rejects_unstarted_day(monkeypatch):
    context = {
        "operational": False,
        "blocked_reason": "CASH_DAY_NOT_STARTED",
    }
    monkeypatch.setattr(cash_context_service, "get_user_cash_context", lambda *_: context)

    with pytest.raises(HTTPException) as error:
        cash_context_service.require_operational_context(
            MagicMock(),
            7,
            SimpleNamespace(id=10),
        )

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "CASH_DAY_NOT_STARTED"


def test_close_branch_rejects_open_boxes(monkeypatch):
    day = SimpleNamespace(id=1)
    branch_day = SimpleNamespace(status="OPEN")
    db = MagicMock()
    db.scalar.side_effect = [branch_day, 99]
    monkeypatch.setattr(cash_day_service, "require_open_day", lambda *_: day)

    with pytest.raises(HTTPException) as error:
        cash_day_service.close_branch(db, 7, 3, SimpleNamespace(email="admin@test.local"))

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "CASH_BRANCH_HAS_OPEN_BOXES"


def test_close_day_rejects_open_branches(monkeypatch):
    day = SimpleNamespace(id=1)
    db = MagicMock()
    db.scalar.return_value = 55
    monkeypatch.setattr(cash_day_service, "require_open_day", lambda *_: day)

    with pytest.raises(HTTPException) as error:
        cash_day_service.close_day(db, 7, SimpleNamespace(email="admin@test.local"))

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "CASH_DAY_HAS_OPEN_BRANCHES"


def test_close_branch_allows_closed_boxes(monkeypatch):
    day = SimpleNamespace(id=1)
    branch_day = SimpleNamespace(
        status="OPEN",
        closed_at=None,
        closed_by=None,
        updated_at=None,
    )
    db = MagicMock()
    db.scalar.side_effect = [branch_day, None]
    monkeypatch.setattr(cash_day_service, "require_open_day", lambda *_: day)

    result = cash_day_service.close_branch(
        db,
        7,
        3,
        SimpleNamespace(email="admin@test.local"),
    )

    assert result.status == "CLOSED"
    assert result.closed_by == "admin@test.local"
    db.flush.assert_called_once()


def test_close_register_calculates_arqueo(monkeypatch):
    day = SimpleNamespace(id=1)
    register = SimpleNamespace(
        id=20,
        cash_day_id=1,
        status="OPEN",
        expected_cash=None,
        counted_cash=None,
        difference=None,
        closing_notes=None,
        closed_at=None,
        closed_by=None,
        updated_at=None,
    )
    db = MagicMock()
    db.scalar.return_value = register
    monkeypatch.setattr(cash_day_service, "require_open_day", lambda *_: day)

    summary = {
        "expected_cash": Decimal("100000.00"),
        "difference": Decimal("5000.00"),
    }
    monkeypatch.setattr(
        "UsersAPI.domains.cash.services.cash_service.CashService._summary",
        lambda *_: summary,
    )

    result = cash_day_service.close_register(
        db,
        7,
        20,
        Decimal("105000.00"),
        "Arqueo correcto",
        SimpleNamespace(email="admin@test.local"),
    )

    assert result.status == "CLOSED"
    assert result.expected_cash == Decimal("100000.00")
    assert result.counted_cash == Decimal("105000.00")
    assert result.difference == Decimal("5000.00")
    assert result.closing_notes == "Arqueo correcto"
    assert result.closed_by == "admin@test.local"
    db.flush.assert_called_once()
