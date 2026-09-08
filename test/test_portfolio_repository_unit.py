from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from UsersAPI.domains.portfolio.repositories.portfolio_repository import PortfolioRepository


class FakeDB:
    def __init__(self):
        self.added = []
        self.scalar_value = None
        self.scalars_value = []

    def add(self, value):
        self.added.append(value)

    def scalar(self, _query):
        return self.scalar_value

    def scalars(self, _query):
        return self.scalars_value


def test_credit_limit_lookup_and_insert():
    db = FakeDB()
    credit = SimpleNamespace(id=uuid4())
    db.scalar_value = credit
    repository = PortfolioRepository(db)

    assert repository.get_credit_limit(1, uuid4()) is credit
    assert repository.get_credit_limit(1, uuid4(), lock=True) is credit

    created = SimpleNamespace(id=uuid4())
    assert repository.add_credit_limit(created) is created
    assert db.added == [created]


def test_obligation_queries_and_insert():
    db = FakeDB()
    first = SimpleNamespace(id=uuid4())
    second = SimpleNamespace(id=uuid4())
    db.scalar_value = first
    db.scalars_value = [first, second]
    repository = PortfolioRepository(db)

    assert repository.list_obligations(1) == [first, second]
    assert repository.list_obligations(1, client_id=uuid4()) == [first, second]
    assert repository.list_obligations(1, date_from=date(2026, 1, 1)) == [first, second]
    assert repository.list_obligations(1, date_to=date(2026, 1, 31)) == [first, second]
    assert repository.list_obligations(
        1,
        client_id=uuid4(),
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
    ) == [first, second]
    assert repository.get_obligation(1, uuid4()) is first
    assert repository.get_obligation(1, uuid4(), lock=True) is first
    assert repository.get_obligation_by_sale(1, uuid4()) is first
    assert repository.get_obligation_by_sale(1, uuid4(), lock=True) is first

    created = SimpleNamespace(id=uuid4())
    assert repository.add_obligation(created) is created
    assert db.added == [created]


def test_payment_queries_and_insert():
    db = FakeDB()
    payment = SimpleNamespace(id=uuid4())
    db.scalar_value = payment
    repository = PortfolioRepository(db)

    assert repository.get_payment(1, payment.id) is payment
    created = SimpleNamespace(id=uuid4())
    assert repository.add_payment(created) is created
    assert db.added == [created]


def test_credit_used_returns_value_and_zero():
    db = FakeDB()
    repository = PortfolioRepository(db)
    db.scalar_value = Decimal("325.50")

    assert repository.credit_used(1, uuid4()) == Decimal("325.50")

    db.scalar_value = None
    assert repository.credit_used(1, uuid4()) == 0
