from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from UsersAPI.domains.inventory.models import InventoryDB, InventoryMovementDB, ProductDB  # noqa: F401
from UsersAPI.domains.inventory.schemas import (
    InventoryMovementCreate,
    InventoryTypeCreate,
    InventoryTypeUpdate,
    ProductCreate,
    ProductUpdate,
)
from UsersAPI.domains.inventory.services import inventory_movement_service as movement_service
from UsersAPI.domains.inventory.services import inventory_service
from UsersAPI.domains.inventory.services import inventory_type_service as type_service
from UsersAPI.domains.inventory.services import product_service


class FakeRepository:
    def __init__(self, value=None):
        self.value = value
        self.saved = []

    def add(self, value):
        self.saved.append(value)
        return value

    def save(self, value):
        self.saved.append(value)
        return value

    def get_by_code(self, *_args):
        return self.value

    def get_by_id(self, *_args):
        return self.value

    def list(self, *_args, **_kwargs):
        return self.value or []


def user():
    return SimpleNamespace(email="user@test.local")


def test_inventory_type_service_create_and_list(monkeypatch):
    repository = FakeRepository()
    monkeypatch.setattr(type_service, "InventoryTypeRepository", lambda _db: repository)

    result = type_service.create_inventory_type(
        InventoryTypeCreate(code="  liq ", name=" Licores "),
        MagicMock(),
        7,
        user(),
    )

    assert result.code == "LIQ"
    assert result.name == "Licores"
    assert result.tenant_id == 7
    assert type_service.list_inventory_types(MagicMock(), 7) == []


def test_inventory_type_service_rejects_duplicate_and_updates(monkeypatch):
    existing = SimpleNamespace(id=2, code="LIQ", name="Licores", active=True)
    repository = FakeRepository(existing)
    monkeypatch.setattr(type_service, "InventoryTypeRepository", lambda _db: repository)

    with pytest.raises(HTTPException) as error:
        type_service.create_inventory_type(
            InventoryTypeCreate(code="liq", name="Other"), MagicMock(), 7, user()
        )
    assert error.value.status_code == 409

    repository.value = existing
    updated = type_service.update_inventory_type(
        2,
        InventoryTypeUpdate(name=" Updated ", active=False),
        MagicMock(),
        7,
        user(),
    )
    assert updated.name == "Updated"
    assert updated.active is False


def test_inventory_type_service_not_found_and_duplicate_update(monkeypatch):
    repository = FakeRepository()
    monkeypatch.setattr(type_service, "InventoryTypeRepository", lambda _db: repository)

    with pytest.raises(HTTPException) as error:
        type_service.update_inventory_type(
            1, InventoryTypeUpdate(name="X"), MagicMock(), 7, user()
        )
    assert error.value.status_code == 404

    current = SimpleNamespace(id=1, code="A", name="A", active=True)
    duplicate = SimpleNamespace(id=2, code="B")
    repository.value = current
    original = repository.get_by_code
    repository.get_by_code = lambda tenant_id, code: (
        duplicate if code == "B" else original(tenant_id, code)
    )

    with pytest.raises(HTTPException) as error:
        type_service.update_inventory_type(
            1, InventoryTypeUpdate(code="B"), MagicMock(), 7, user()
        )
    assert error.value.status_code == 409


def test_product_service_create_initializes_zero_inventory(monkeypatch):
    product_repo = FakeRepository()
    inventory_repo = FakeRepository()
    type_repo = FakeRepository(SimpleNamespace(id=3, active=True))
    monkeypatch.setattr(product_service, "ProductRepository", lambda _db: product_repo)
    monkeypatch.setattr(product_service, "InventoryRepository", lambda _db: inventory_repo)
    monkeypatch.setattr(product_service, "InventoryTypeRepository", lambda _db: type_repo)

    product_repo.add = lambda product: (setattr(product, "id", 11) or product)
    result = product_service.create_product(
        ProductCreate(code="p1", name="Product 1", inventory_type_id=3),
        MagicMock(),
        7,
        user(),
    )

    assert result.id == 11
    assert inventory_repo.saved[0].quantity == 0
    assert inventory_repo.saved[0].product_id == 11


def test_product_service_duplicate_and_invalid_type(monkeypatch):
    product_repo = FakeRepository(SimpleNamespace(id=1))
    type_repo = FakeRepository()
    monkeypatch.setattr(product_service, "ProductRepository", lambda _db: product_repo)
    monkeypatch.setattr(product_service, "InventoryTypeRepository", lambda _db: type_repo)
    monkeypatch.setattr(product_service, "InventoryRepository", lambda _db: FakeRepository())

    with pytest.raises(HTTPException) as error:
        product_service.create_product(
            ProductCreate(code="P1", name="Product", inventory_type_id=1),
            MagicMock(),
            7,
            user(),
        )
    assert error.value.status_code == 409

    product_repo.value = None
    with pytest.raises(HTTPException) as error:
        product_service.create_product(
            ProductCreate(code="P1", name="Product", inventory_type_id=1),
            MagicMock(),
            7,
            user(),
        )
    assert error.value.status_code == 400


def test_product_service_update(monkeypatch):
    product = SimpleNamespace(
        id=4,
        code="P4",
        name="Old",
        inventory_type_id=1,
        active=True,
    )
    repository = FakeRepository(product)
    type_repo = FakeRepository(SimpleNamespace(id=2, active=True))
    monkeypatch.setattr(product_service, "ProductRepository", lambda _db: repository)
    monkeypatch.setattr(product_service, "InventoryTypeRepository", lambda _db: type_repo)

    result = product_service.update_product(
        4,
        ProductUpdate(code=" p5 ", name=" New ", inventory_type_id=2, active=False),
        MagicMock(),
        7,
        user(),
    )
    assert result.code == "P5"
    assert result.name == "New"
    assert result.inventory_type_id == 2
    assert result.active is False


def test_inventory_service_calculates_values(monkeypatch):
    inventory = InventoryDB(
        tenant_id=7,
        product_id=1,
        quantity=Decimal("20"),
        purchase_price=Decimal("17000"),
        profit_percentage=Decimal("0.50"),
        created_by="system",
    )
    movement = InventoryMovementDB(
        tenant_id=7,
        product_id=1,
        movement_type="ENTRY",
        origin_type="PURCHASE",
        quantity=Decimal("20"),
        balance_before=Decimal("0"),
        balance_after=Decimal("20"),
        created_by="system",
    )
    assert movement.movement_type == "ENTRY"

    repo = MagicMock()
    repo.list.return_value = [inventory]
    repo.get_by_product.return_value = inventory
    monkeypatch.setattr(inventory_service, "InventoryRepository", lambda _db: repo)

    assert inventory_service.list_inventory(MagicMock(), 7)[0].total_inventory == Decimal("340000")
    assert inventory_service.get_inventory(1, MagicMock(), 7).sale_price == Decimal("25500.00")


def test_inventory_service_not_found(monkeypatch):
    repo = MagicMock()
    repo.get_by_product.return_value = None
    monkeypatch.setattr(inventory_service, "InventoryRepository", lambda _db: repo)
    with pytest.raises(HTTPException) as error:
        inventory_service.get_inventory(1, MagicMock(), 7)
    assert error.value.status_code == 404


def movement_fixture(quantity=Decimal("10"), active=True):
    product = ProductDB(
        id=1,
        tenant_id=7,
        inventory_type_id=1,
        code="P1",
        name="Product",
        active=active,
        created_by="system",
    )
    inventory = InventoryDB(
        id=1,
        tenant_id=7,
        product_id=1,
        quantity=quantity,
        purchase_price=Decimal("100"),
        profit_percentage=Decimal("0.5"),
        created_by="system",
    )
    return product, inventory


def test_movement_entry_updates_inventory_and_creates_history(monkeypatch):
    product, inventory = movement_fixture()
    product_repo = MagicMock()
    inventory_repo = MagicMock()
    movement_repo = MagicMock()
    product_repo.get_by_id.return_value = product
    inventory_repo.get_by_product.return_value = inventory
    movement_repo.add.side_effect = lambda value: value
    monkeypatch.setattr(movement_service, "ProductRepository", lambda _db: product_repo)
    monkeypatch.setattr(movement_service, "InventoryRepository", lambda _db: inventory_repo)
    monkeypatch.setattr(movement_service, "InventoryMovementRepository", lambda _db: movement_repo)

    result = movement_service.create_inventory_movement(
        InventoryMovementCreate(
            product_id=1,
            movement_type="ENTRY",
            origin_type="PURCHASE",
            quantity=5,
            unit_purchase_price=120,
            profit_percentage=Decimal("0.25"),
        ),
        MagicMock(),
        7,
        user(),
    )

    assert result.balance_before == Decimal("10")
    assert result.balance_after == Decimal("15")
    assert inventory.quantity == Decimal("15")
    assert inventory.purchase_price == Decimal("120")
    inventory_repo.save.assert_called_once_with(inventory)


def test_movement_exit_rejects_insufficient_stock(monkeypatch):
    product, inventory = movement_fixture(quantity=Decimal("2"))
    product_repo = MagicMock()
    inventory_repo = MagicMock()
    product_repo.get_by_id.return_value = product
    inventory_repo.get_by_product.return_value = inventory
    monkeypatch.setattr(movement_service, "ProductRepository", lambda _db: product_repo)
    monkeypatch.setattr(movement_service, "InventoryRepository", lambda _db: inventory_repo)

    with pytest.raises(HTTPException) as error:
        movement_service.create_inventory_movement(
            InventoryMovementCreate(
                product_id=1,
                movement_type="EXIT",
                origin_type="SALE",
                quantity=3,
                origin_id=uuid4(),
            ),
            MagicMock(),
            7,
            user(),
        )
    assert error.value.status_code == 409


def test_movement_validates_origin_product_and_inventory(monkeypatch):
    with pytest.raises(HTTPException) as error:
        movement_service.create_inventory_movement(
            InventoryMovementCreate(
                product_id=1, movement_type="ENTRY", origin_type="UNKNOWN", quantity=1
            ),
            MagicMock(),
            7,
            user(),
        )
    assert error.value.status_code == 400

    product_repo = MagicMock()
    product_repo.get_by_id.return_value = None
    monkeypatch.setattr(movement_service, "ProductRepository", lambda _db: product_repo)
    with pytest.raises(HTTPException) as error:
        movement_service.create_inventory_movement(
            InventoryMovementCreate(
                product_id=1, movement_type="ENTRY", origin_type="PURCHASE", quantity=1
            ),
            MagicMock(),
            7,
            user(),
        )
    assert error.value.status_code == 404

    product, _ = movement_fixture(active=False)
    product_repo.get_by_id.return_value = product
    with pytest.raises(HTTPException) as error:
        movement_service.create_inventory_movement(
            InventoryMovementCreate(
                product_id=1, movement_type="ENTRY", origin_type="PURCHASE", quantity=1
            ),
            MagicMock(),
            7,
            user(),
        )
    assert error.value.status_code == 409

    product, _ = movement_fixture()
    product_repo.get_by_id.return_value = product
    inventory_repo = MagicMock()
    inventory_repo.get_by_product.return_value = None
    monkeypatch.setattr(movement_service, "InventoryRepository", lambda _db: inventory_repo)
    with pytest.raises(HTTPException) as error:
        movement_service.create_inventory_movement(
            InventoryMovementCreate(
                product_id=1, movement_type="ENTRY", origin_type="PURCHASE", quantity=1
            ),
            MagicMock(),
            7,
            user(),
        )
    assert error.value.status_code == 404


def test_movement_rejects_wrong_origin_direction(monkeypatch):
    product, _ = movement_fixture()
    product_repo = MagicMock()
    product_repo.get_by_id.return_value = product
    monkeypatch.setattr(movement_service, "ProductRepository", lambda _db: product_repo)

    for movement_type, origin_type in (("ENTRY", "SALE"), ("EXIT", "PURCHASE")):
        with pytest.raises(HTTPException) as error:
            movement_service.create_inventory_movement(
                InventoryMovementCreate(
                    product_id=1,
                    movement_type=movement_type,
                    origin_type=origin_type,
                    quantity=1,
                ),
                MagicMock(),
                7,
                user(),
            )
        assert error.value.status_code == 400
