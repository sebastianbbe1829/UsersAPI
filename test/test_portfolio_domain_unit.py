from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from UsersAPI.domains.portfolio.models.obligation import ObligationDB
from UsersAPI.domains.portfolio.schemas.portfolio import CreditLimitUpdate
from UsersAPI.domains.portfolio.services.portfolio_service import (
    get_client_credit,
    list_client_obligations,
    list_obligations,
    list_payments,
    register_payment,
    upsert_client_credit_limit,
)


def test_get_client_credit(monkeypatch):
    client_id = uuid4()
    credit = SimpleNamespace(
        client_id=client_id,
        approved_limit=Decimal("5000.00"),
        active=True,
        updated_at=None,
        updated_by=None,
    )
    repository = SimpleNamespace(
        get_credit_limit=lambda *_args, **_kwargs: credit,
        credit_used=lambda *_args, **_kwargs: Decimal("1250.00"),
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        lambda _db: repository,
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )

    result = get_client_credit(client_id, SimpleNamespace(), 1)

    assert result.approved_limit == Decimal("5000.00")
    assert result.credit_used == Decimal("1250.00")
    assert result.credit_available == Decimal("3750.00")


def test_get_client_credit_without_limit(monkeypatch):
    client_id = uuid4()
    repository = SimpleNamespace(get_credit_limit=lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        lambda _db: repository,
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )

    with pytest.raises(HTTPException) as exc_info:
        get_client_credit(client_id, SimpleNamespace(), 1)

    assert exc_info.value.status_code == 404


def test_get_client_credit_rejects_missing_client():
    db = SimpleNamespace(scalar=lambda _query: None)

    with pytest.raises(HTTPException) as exc_info:
        get_client_credit(uuid4(), db, 1)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Client not found"


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
        CreditLimitUpdate(approved_limit=Decimal("1500.50")),
        db,
        1,
        SimpleNamespace(email="admin@test.com"),
    )

    assert result.approved_limit == Decimal("1500.50")
    assert result.created_by == "admin@test.com"
    assert result.active is True


def test_upsert_client_credit_limit_updates_existing_limit(monkeypatch):
    client_id = uuid4()
    credit = SimpleNamespace(
        client_id=client_id,
        approved_limit=Decimal("1000.00"),
        active=False,
        updated_at=None,
        updated_by=None,
    )
    repository = SimpleNamespace(
        get_credit_limit=lambda *_args, **_kwargs: credit,
        credit_used=lambda *_args, **_kwargs: Decimal("250.00"),
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
        CreditLimitUpdate(approved_limit=Decimal("900.00")),
        db,
        1,
        SimpleNamespace(username="operator"),
    )

    assert result.approved_limit == Decimal("900.00")
    assert result.updated_by == "operator"
    assert result.active is True


def test_upsert_client_credit_limit_rejects_limit_below_usage(monkeypatch):
    client_id = uuid4()
    credit = SimpleNamespace(
        client_id=client_id,
        approved_limit=Decimal("1000.00"),
        active=True,
        updated_at=None,
        updated_by=None,
    )
    repository = SimpleNamespace(
        get_credit_limit=lambda *_args, **_kwargs: credit,
        credit_used=lambda *_args, **_kwargs: Decimal("800.00"),
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        lambda _db: repository,
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )

    with pytest.raises(HTTPException) as exc_info:
        upsert_client_credit_limit(
            client_id,
            CreditLimitUpdate(approved_limit=Decimal("799.99")),
            SimpleNamespace(flush=lambda: None),
            1,
            SimpleNamespace(email="admin@test.com"),
        )

    assert exc_info.value.status_code == 409
    assert "cannot be lower" in exc_info.value.detail.lower()


def test_list_obligations_delegates_to_repository(monkeypatch):
    obligations = [SimpleNamespace(id=uuid4())]
    repository = SimpleNamespace(list_obligations=lambda *_args, **_kwargs: obligations)
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        lambda _db: repository,
    )

    assert list_obligations(SimpleNamespace(), 7) == obligations


def test_list_client_obligations_filters_by_client(monkeypatch):
    client_id = uuid4()
    obligations = [SimpleNamespace(id=uuid4())]
    repository = SimpleNamespace(list_obligations=lambda *_args, **_kwargs: obligations)
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        lambda _db: repository,
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )

    assert list_client_obligations(client_id, SimpleNamespace(), 7) == obligations


def _payment_data(client_id, obligation_id, amount="100.00"):
    from UsersAPI.domains.portfolio.schemas.portfolio import PaymentCreate

    return PaymentCreate(
        client_id=client_id,
        payment_method=" cash ",
        amount=Decimal(amount),
        allocations=[
            {"obligation_id": obligation_id, "amount": Decimal(amount)}
        ],
    )


def test_register_payment_rejects_allocation_total(monkeypatch):
    client_id = uuid4()
    obligation_id = uuid4()
    data = _payment_data(client_id, obligation_id)
    data.allocations[0].amount = Decimal("90.00")
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )

    with pytest.raises(HTTPException) as exc_info:
        register_payment(data, SimpleNamespace(), 1, SimpleNamespace())

    assert exc_info.value.status_code == 400


def test_register_payment_rejects_unknown_obligation(monkeypatch):
    client_id = uuid4()
    obligation_id = uuid4()
    data = _payment_data(client_id, obligation_id)
    repository = SimpleNamespace(get_obligation=lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        lambda _db: repository,
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )

    with pytest.raises(HTTPException) as exc_info:
        register_payment(data, SimpleNamespace(), 1, SimpleNamespace())

    assert exc_info.value.status_code == 404


def test_register_payment_rejects_wrong_client(monkeypatch):
    client_id = uuid4()
    obligation_id = uuid4()
    data = _payment_data(client_id, obligation_id)
    obligation = SimpleNamespace(
        client_id=uuid4(), status="ACTIVE", balance=Decimal("200.00")
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

    with pytest.raises(HTTPException) as exc_info:
        register_payment(data, SimpleNamespace(), 1, SimpleNamespace())

    assert exc_info.value.status_code == 409


def test_register_payment_rejects_inactive_obligation(monkeypatch):
    client_id = uuid4()
    obligation_id = uuid4()
    data = _payment_data(client_id, obligation_id)
    obligation = SimpleNamespace(
        client_id=client_id, status="SETTLED", balance=Decimal("200.00")
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

    with pytest.raises(HTTPException) as exc_info:
        register_payment(data, SimpleNamespace(), 1, SimpleNamespace())

    assert exc_info.value.status_code == 409


def test_register_payment_rejects_amount_above_balance(monkeypatch):
    client_id = uuid4()
    obligation_id = uuid4()
    data = _payment_data(client_id, obligation_id)
    obligation = SimpleNamespace(
        id=obligation_id,
        client_id=client_id,
        status="ACTIVE",
        balance=Decimal("50.00"),
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

    with pytest.raises(HTTPException) as exc_info:
        register_payment(data, SimpleNamespace(), 1, SimpleNamespace())

    assert exc_info.value.status_code == 409


def test_register_payment_applies_partial_payment(monkeypatch):
    client_id = uuid4()
    obligation_id = uuid4()
    data = _payment_data(client_id, obligation_id)
    obligation = SimpleNamespace(
        id=obligation_id,
        client_id=client_id,
        status="ACTIVE",
        balance=Decimal("200.00"),
        sale_id=uuid4(),
        updated_at=None,
        updated_by=None,
    )
    repository = SimpleNamespace(
        get_obligation=lambda *_args, **_kwargs: obligation,
        add_payment=lambda _payment: None,
        get_payment=lambda *_args, **_kwargs: None,
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

    result = register_payment(data, db, 1, SimpleNamespace(email="cashier"))

    assert result.amount == Decimal("100.00")
    assert result.payment_method == "CASH"
    assert obligation.balance == Decimal("100.00")
    assert obligation.status == "ACTIVE"
    assert len(result.allocations) == 1


def test_register_payment_settles_obligation_and_sale(monkeypatch):
    client_id = uuid4()
    obligation_id = uuid4()
    sale_id = uuid4()
    data = _payment_data(client_id, obligation_id)
    obligation = SimpleNamespace(
        id=obligation_id,
        client_id=client_id,
        status="ACTIVE",
        balance=Decimal("100.00"),
        sale_id=sale_id,
        updated_at=None,
        updated_by=None,
    )
    sale = SimpleNamespace(status="PENDING", updated_at=None, updated_by=None)
    repository = SimpleNamespace(
        get_obligation=lambda *_args, **_kwargs: obligation,
        add_payment=lambda _payment: None,
        get_payment=lambda *_args, **_kwargs: None,
    )
    db = SimpleNamespace(flush=lambda: None, scalar=lambda _query: sale)
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service.PortfolioRepository",
        lambda _db: repository,
    )
    monkeypatch.setattr(
        "UsersAPI.domains.portfolio.services.portfolio_service._client",
        lambda *_args, **_kwargs: SimpleNamespace(id=client_id),
    )

    register_payment(data, db, 1, SimpleNamespace(email="cashier"))

    assert obligation.balance == Decimal("0.00")
    assert obligation.status == "SETTLED"
    assert sale.status == "COMPLETED"
    assert sale.updated_by == "cashier"


def test_list_payments_supports_client_filter():
    payment = SimpleNamespace(id=uuid4())
    scalar_result = SimpleNamespace(unique=lambda: [payment])
    db = SimpleNamespace(scalars=lambda _query: scalar_result)

    result = list_payments(db, 1, uuid4())

    assert result == [payment]


def test_obligation_sale_number_property():
    obligation = ObligationDB()
    obligation.sale = SimpleNamespace(sale_number="V-000123")
    assert obligation.sale_number == "V-000123"

    obligation.sale = None
    assert obligation.sale_number is None
