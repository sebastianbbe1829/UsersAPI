from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from UsersAPI.domains.sales.repositories import SaleRepository
from UsersAPI.domains.sales.schemas import SaleCreate, SaleItemCreate, SalePaymentCreate
from UsersAPI.domains.sales.services import sale_service


def user():
    return SimpleNamespace(email="sales@test.local")


def inventory(quantity="10", purchase_price="100", profit="0.10"):
    return SimpleNamespace(
        quantity=Decimal(quantity),
        purchase_price=Decimal(purchase_price),
        profit_percentage=Decimal(profit),
    )


def test_sale_price_uses_inventory_profit_as_fraction():
    assert sale_service._sale_price(inventory()) == Decimal("110.00")


def test_sale_price_rejects_empty_inventory():
    with pytest.raises(HTTPException) as error:
        sale_service._sale_price(inventory(quantity="0"))
    assert error.value.status_code == 409


def test_sale_price_rejects_inventory_without_cost():
    item = inventory()
    item.purchase_price = None
    with pytest.raises(HTTPException) as error:
        sale_service._sale_price(item)
    assert error.value.status_code == 409


def test_sale_repository_generates_next_number():
    db = MagicMock()
    db.execute.return_value.scalar_one.return_value = 12
    repository = SaleRepository(db)

    assert repository.next_sale_number(7) == "VTA-000013"
    db.execute.assert_called()


def test_sale_repository_get_and_list_are_tenant_scoped():
    db = MagicMock()
    db.scalars.return_value.unique.return_value.first.return_value = "sale"
    repository = SaleRepository(db)

    assert repository.get_by_id(7, uuid4()) == "sale"

    db.scalars.return_value.unique.return_value.__iter__.return_value = iter(["a", "b"])
    assert repository.list(7, limit=2, offset=1) == ["a", "b"]


def test_create_sale_rejects_duplicate_products_before_database_work():
    data = SaleCreate(
        items=[
            SaleItemCreate(product_id=1, quantity=1),
            SaleItemCreate(product_id=1, quantity=2),
        ],
        payments=[SalePaymentCreate(payment_method="cash", amount=Decimal("100"))],
    )

    with pytest.raises(HTTPException) as error:
        sale_service.create_sale(data, MagicMock(), 7, user())
    assert error.value.status_code == 400
    assert "more than once" in error.value.detail


def test_create_sale_rejects_payment_total_mismatch():
    db = MagicMock()
    db.execute.return_value.scalar_one.return_value = 0
    db.scalar.side_effect = [
        inventory(),
        SimpleNamespace(id=1, code="PROD-000001", name="Product", active=True),
    ]
    data = SaleCreate(
        items=[SaleItemCreate(product_id=1, quantity=2)],
        payments=[SalePaymentCreate(payment_method="cash", amount=Decimal("1"))],
    )

    with pytest.raises(HTTPException) as error:
        sale_service.create_sale(data, db, 7, user())
    assert error.value.status_code == 400
    assert "Payment total must equal sale total" in error.value.detail


def test_get_and_list_sales_delegate_to_repository(monkeypatch):
    repository = MagicMock()
    repository.get_by_id.return_value = "sale"
    repository.list.return_value = ["sale"]
    monkeypatch.setattr(sale_service, "SaleRepository", lambda _db: repository)

    assert sale_service.get_sale(uuid4(), MagicMock(), 7) == "sale"
    assert sale_service.list_sales(MagicMock(), 7, limit=10, offset=2) == ["sale"]
