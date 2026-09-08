from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from UsersAPI.domains.sales import services as sale_service
from UsersAPI.domains.sales.schemas import (
    SaleCreate,
    SaleItemCreate,
    SalePaymentCreate,
)


def inventory(quantity="10", purchase_price="100", profit_percentage="0.2"):
    return SimpleNamespace(
        quantity=Decimal(quantity),
        purchase_price=Decimal(purchase_price),
        profit_percentage=Decimal(profit_percentage),
    )


def user():
    return SimpleNamespace(email="user@example.com")


def test_sale_price_requires_available_inventory():
    with pytest.raises(HTTPException) as error:
        sale_service._sale_price(inventory(quantity="0"))
    assert error.value.status_code == 409


def test_actor_name_falls_back_to_username_and_system():
    assert sale_service._actor_name(SimpleNamespace(username="john")) == "john"
    assert sale_service._actor_name(None) == "system"


def test_create_sale_rejects_duplicate_products():
    data = SaleCreate(
        items=[
            SaleItemCreate(product_id=1, quantity=1),
            SaleItemCreate(product_id=1, quantity=2),
        ],
        payments=[SalePaymentCreate(payment_method="cash", amount=1)],
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
    assert "Payment total" in error.value.detail


def test_get_sale_not_found():
    repository = MagicMock()
    repository.get_by_id.return_value = None
    sale_service.SaleRepository = lambda db: repository
    with pytest.raises(HTTPException) as error:
        sale_service.get_sale(uuid4(), MagicMock(), 7)
    assert error.value.status_code == 404
