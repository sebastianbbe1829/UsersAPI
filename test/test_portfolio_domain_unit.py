from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from UsersAPI.domains.portfolio.schemas import CreditLimitUpdate, PaymentCreate
from UsersAPI.domains.portfolio.services.portfolio_service import register_payment


def test_credit_limit_rejects_negative_amount():
    with pytest.raises(ValidationError):
        CreditLimitUpdate(approved_limit=Decimal("-1"))


def test_payment_rejects_duplicate_obligations():
    obligation_id = uuid4()
    with pytest.raises(ValidationError):
        PaymentCreate(
            client_id=uuid4(),
            payment_method="TRANSFERENCIA",
            amount=Decimal("100"),
            allocations=[
                {"obligation_id": obligation_id, "amount": Decimal("50")},
                {"obligation_id": obligation_id, "amount": Decimal("50")},
            ],
        )


def test_payment_requires_allocations_to_equal_amount():
    db = SimpleNamespace()
    current_user = SimpleNamespace(email="admin@test.com")
    data = PaymentCreate(
        client_id=uuid4(),
        payment_method="TRANSFERENCIA",
        amount=Decimal("100"),
        allocations=[{"obligation_id": uuid4(), "amount": Decimal("90")}],
    )
    db.scalar = lambda *_args, **_kwargs: SimpleNamespace(id=data.client_id)
    with pytest.raises(HTTPException, match="Payment allocations must equal payment amount"):
        register_payment(data, db, 1, current_user)


def test_payment_rejects_obligation_from_another_client(monkeypatch):
    client_id = uuid4()
    other_client_id = uuid4()
    obligation_id = uuid4()
    data = PaymentCreate(
        client_id=client_id,
        payment_method="TRANSFERENCIA",
        amount=Decimal("100"),
        allocations=[{"obligation_id": obligation_id, "amount": Decimal("100")}],
    )
    client = SimpleNamespace(id=client_id)
    obligation = SimpleNamespace(
        id=obligation_id,
        client_id=other_client_id,
        status="ACTIVE",
        balance=Decimal("100"),
    )

    class Repository:
        def __init__(self, _db):
            pass

        def get_obligation(self, *_args, **_kwargs):
            return obligation

    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        Repository,
    )
    db = SimpleNamespace(scalar=lambda *_args, **_kwargs: client)
    with pytest.raises(HTTPException, match="does not belong"):
        register_payment(data, db, 1, SimpleNamespace(email="admin@test.com"))
