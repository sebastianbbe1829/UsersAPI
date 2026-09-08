from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from UsersAPI.domains.portfolio.schemas import CreditLimitUpdate, PaymentCreate
from UsersAPI.domains.portfolio.services.portfolio_service import (
    get_client_credit,
    list_client_obligations,
    list_obligations,
    list_payments,
    register_payment,
    upsert_client_credit_limit,
)


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


def test_payment_requires_allocations_to_equal_amount(monkeypatch):
    client_id = uuid4()
    data = PaymentCreate(
        client_id=client_id,
        payment_method="TRANSFERENCIA",
        amount=Decimal("100"),
        allocations=[{"obligation_id": uuid4(), "amount": Decimal("90")}],
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )
    with pytest.raises(
        HTTPException, match="Payment allocations must equal payment amount"
    ):
        register_payment(data, SimpleNamespace(), 1, SimpleNamespace(email="admin@test.com"))


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
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )
    with pytest.raises(HTTPException, match="does not belong"):
        register_payment(data, SimpleNamespace(), 1, SimpleNamespace(email="admin@test.com"))


def test_get_client_credit_returns_usage_and_available(monkeypatch):
    client_id = uuid4()
    credit = SimpleNamespace(
        client_id=client_id,
        approved_limit=Decimal("1000"),
        credit_used=None,
        credit_available=None,
    )

    class Repository:
        def __init__(self, _db):
            pass

        def get_credit_limit(self, *_args, **_kwargs):
            return credit

        def credit_used(self, *_args, **_kwargs):
            return Decimal("250.126")

    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        Repository,
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )
    result = get_client_credit(client_id, SimpleNamespace(), 1)

    assert result.credit_used == Decimal("250.13")
    assert result.credit_available == Decimal("749.87")


def test_get_client_credit_requires_configuration(monkeypatch):
    client_id = uuid4()

    class Repository:
        def __init__(self, _db):
            pass

        def get_credit_limit(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        Repository,
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )
    with pytest.raises(HTTPException, match="Credit limit not configured"):
        get_client_credit(client_id, SimpleNamespace(), 1)


def test_upsert_client_credit_limit_creates_limit(monkeypatch):
    client_id = uuid4()
    repository = SimpleNamespace(
        get_credit_limit=lambda *_args, **_kwargs: None,
        add_credit_limit=lambda credit: setattr(repository, "created", credit),
        credit_used=lambda *_args, **_kwargs: Decimal("0"),
    )
    db = SimpleNamespace(flush=lambda: None)
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        lambda _db: repository,
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._credit_read",
        lambda credit, *_args: credit,
    )

    result = upsert_client_credit_limit(
        client_id,
        CreditLimitUpdate(approved_limit=Decimal("1500.005")),
        db,
        1,
        SimpleNamespace(email="admin@test.com"),
    )

    assert result.approved_limit == Decimal("1500.01")
    assert result.created_by == "admin@test.com"
    assert result.active is True


def test_upsert_client_credit_limit_rejects_limit_below_usage(monkeypatch):
    client_id = uuid4()
    credit = SimpleNamespace(
        approved_limit=Decimal("1000"),
        active=True,
        updated_at=None,
        updated_by=None,
    )
    repository = SimpleNamespace(
        get_credit_limit=lambda *_args, **_kwargs: credit,
        credit_used=lambda *_args, **_kwargs: Decimal("800"),
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        lambda _db: repository,
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )

    with pytest.raises(HTTPException, match="cannot be lower than current credit used"):
        upsert_client_credit_limit(
            client_id,
            CreditLimitUpdate(approved_limit=Decimal("799.99")),
            SimpleNamespace(),
            1,
            SimpleNamespace(email="admin@test.com"),
        )


def test_list_obligations_delegates_to_repository(monkeypatch):
    expected = [SimpleNamespace(id=uuid4())]
    repository = SimpleNamespace(list_obligations=lambda *args, **kwargs: expected)
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        lambda _db: repository,
    )

    assert list_obligations(SimpleNamespace(), 7) == expected


def test_list_client_obligations_validates_client_and_delegates(monkeypatch):
    client_id = uuid4()
    expected = [SimpleNamespace(id=uuid4())]
    repository = SimpleNamespace(list_obligations=lambda *args, **kwargs: expected)
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        lambda _db: repository,
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )

    assert list_client_obligations(client_id, SimpleNamespace(), 7) == expected


def test_list_payments_supports_client_filter():
    expected = [SimpleNamespace(id=uuid4())]
    scalars = SimpleNamespace(unique=lambda: expected)
    db = SimpleNamespace(scalars=lambda _query: scalars)

    assert list_payments(db, 7, uuid4()) == expected


def test_payment_rejects_missing_obligation(monkeypatch):
    client_id = uuid4()
    data = PaymentCreate(
        client_id=client_id,
        payment_method="TRANSFERENCIA",
        amount=Decimal("100"),
        allocations=[{"obligation_id": uuid4(), "amount": Decimal("100")}],
    )
    repository = SimpleNamespace(get_obligation=lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        lambda _db: repository,
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )

    with pytest.raises(HTTPException, match="Obligation not found"):
        register_payment(data, SimpleNamespace(), 1, SimpleNamespace(email="admin@test.com"))


def test_payment_rejects_inactive_obligation(monkeypatch):
    client_id = uuid4()
    obligation_id = uuid4()
    data = PaymentCreate(
        client_id=client_id,
        payment_method="TRANSFERENCIA",
        amount=Decimal("100"),
        allocations=[{"obligation_id": obligation_id, "amount": Decimal("100")}],
    )
    obligation = SimpleNamespace(
        id=obligation_id,
        client_id=client_id,
        status="SETTLED",
        balance=Decimal("100"),
    )
    repository = SimpleNamespace(get_obligation=lambda *_args, **_kwargs: obligation)
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        lambda _db: repository,
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )

    with pytest.raises(HTTPException, match="Only active obligations"):
        register_payment(data, SimpleNamespace(), 1, SimpleNamespace(email="admin@test.com"))


def test_payment_rejects_amount_above_obligation_balance(monkeypatch):
    client_id = uuid4()
    obligation_id = uuid4()
    data = PaymentCreate(
        client_id=client_id,
        payment_method="TRANSFERENCIA",
        amount=Decimal("100"),
        allocations=[{"obligation_id": obligation_id, "amount": Decimal("100")}],
    )
    obligation = SimpleNamespace(
        id=obligation_id,
        client_id=client_id,
        status="ACTIVE",
        balance=Decimal("50"),
    )
    repository = SimpleNamespace(get_obligation=lambda *_args, **_kwargs: obligation)
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        lambda _db: repository,
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )

    with pytest.raises(HTTPException, match="Payment exceeds obligation balance"):
        register_payment(data, SimpleNamespace(), 1, SimpleNamespace(email="admin@test.com"))
