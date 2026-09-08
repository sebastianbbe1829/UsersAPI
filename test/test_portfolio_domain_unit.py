from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from UsersAPI.domains.portfolio.schemas.portfolio import CreditLimitUpdate
from UsersAPI.domains.portfolio.services.portfolio_service import (
    get_client_credit,
    upsert_client_credit_limit,
)


def test_get_client_credit(monkeypatch):
    client_id = uuid4()
    credit = SimpleNamespace(
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
    assert result.used == Decimal("1250.00")
    assert result.available == Decimal("3750.00")


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

    with pytest.raises(ValueError, match="credit limit cannot be lower than current usage"):
        upsert_client_credit_limit(
            client_id,
            CreditLimitUpdate(approved_limit=Decimal("799.99")),
            SimpleNamespace(flush=lambda: None),
            1,
            SimpleNamespace(email="admin@test.com"),
        )
