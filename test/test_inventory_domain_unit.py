import asyncio
import importlib
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from UsersAPI.domains.inventory.controllers import catalog_controller
from UsersAPI.domains.inventory.controllers import inventory_controller
from UsersAPI.domains.inventory.controllers import movement_controller
from UsersAPI.domains.inventory.models import InventoryDB, InventoryMovementDB, ProductDB
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

inventory_routes = importlib.import_module("UsersAPI.domains.inventory.routes.inventory_routes")


class FakeRepository:
    def __init__(self, value=None, next_code_value="PROD-000001"):
        self.value = value
        self.next_code_value = next_code_value
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

    def next_code(self, *_args):
        return self.next_code_value

    def list(self, *_args, **_kwargs):
        return self.value or []


def user():
    return SimpleNamespace(email="user@test.local")


def test_inventory_type_service_create_and_list(monkeypatch):
    repository = FakeRepository()
    monkeypatch.setattr(type_service, "InventoryTypeRepository", lambda _db: repository)

    result = type_service.create_inventory_type(
        InventoryTypeCreate(code="  liq ", name=" Licores "), MagicMock(), 7, user()
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

    updated = type_service.update_inventory_type(
        2, InventoryTypeUpdate(name=" Updated ", active=False), MagicMock(), 7, user()
    )
    assert updated.name == "Updated"
    assert updated.active is False


def test_inventory_type_service_not_found_and_duplicate_update(monkeypatch):
    repository = FakeRepository()
    monkeypatch.setattr(type_service, "InventoryTypeRepository", lambda _db: repository)

    with pytest.raises(HTTPException) as error:
        type_service.update_inventory_type(1, InventoryTypeUpdate(name="X"), MagicMock(), 7, user())
    assert error.value.status_code == 404

    current = SimpleNamespace(id=1, code="A", name="A", active=True)
    duplicate = SimpleNamespace(id=2, code="B")
    repository.value = current
    repository.get_by_code = lambda tenant_id, code: duplicate if code == "B" else None

    with pytest.raises(HTTPException) as error:
        type_service.update_inventory_type(1, InventoryTypeUpdate(code="B"), MagicMock(), 7, user())
    assert error.value.status_code == 409


def test_product_service_generates_code_and_does_not_create_inventory(monkeypatch):
    product_repo = FakeRepository(next_code_value="PROD-000001")
    type_repo = FakeRepository(SimpleNamespace(id=3, active=True))
    monkeypatch.setattr(product_service, "ProductRepository", lambda _db: product_repo)
    monkeypatch.setattr(product_service, "InventoryTypeRepository", lambda _db: type_repo)

    result = product_service.create_product(
        ProductCreate(name=" Product 1 ", inventory_type_id=3), MagicMock(), 7, user()
    )

    assert result.code == "PROD-000001"
    assert result.name == "Product 1"
    assert result.tenant_id == 7
    assert len(product_repo.saved) == 1
    assert product_repo.saved[0].code == "PROD-000001"


def test_product_service_generates_next_code_per_tenant(monkeypatch):
    repository = FakeRepository(next_code_value="PROD-000002")
    type_repo = FakeRepository(SimpleNamespace(id=3, active=True))
    monkeypatch.setattr(product_service, "ProductRepository", lambda _db: repository)
    monkeypatch.setattr(product_service, "InventoryTypeRepository", lambda _db: type_repo)

    result = product_service.create_product(
        ProductCreate(name="Product 2", inventory_type_id=3), MagicMock(), 7, user()
    )

    assert result.code == "PROD-000002"


def test_product_service_invalid_type(monkeypatch):
    product_repo = FakeRepository(next_code_value="PROD-000001")
    type_repo = FakeRepository()
    monkeypatch.setattr(product_service, "ProductRepository", lambda _db: product_repo)
    monkeypatch.setattr(product_service, "InventoryTypeRepository", lambda _db: type_repo)

    with pytest.raises(HTTPException) as error:
        product_service.create_product(
            ProductCreate(name="Product", inventory_type_id=1), MagicMock(), 7, user()
        )
    assert error.value.status_code == 400
    assert product_repo.saved == []


def test_product_service_update_keeps_code_immutable(monkeypatch):
    product = SimpleNamespace(
        id=4,
        code="PROD-000004",
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
        ProductUpdate(name=" New ", inventory_type_id=2, active=False),
        MagicMock(),
        7,
        user(),
    )

    assert result.code == "PROD-000004"
    assert result.name == "New"
    assert result.inventory_type_id == 2
    assert result.active is False


def test_product_service_not_found(monkeypatch):
    repository = FakeRepository()
    monkeypatch.setattr(product_service, "ProductRepository", lambda _db: repository)

    with pytest.raises(HTTPException) as error:
        product_service.update_product(99, ProductUpdate(name="X"), MagicMock(), 7, user())
    assert error.value.status_code == 404


def movement_fixture(quantity=Decimal("10"), active=True):
    product = ProductDB(
        id=1,
        tenant_id=7,
        inventory_type_id=1,
        code="PROD-000001",
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


def test_inventory_service_calculates_values(monkeypatch):
    inventory = InventoryDB(
        tenant_id=7,
        product_id=1,
        quantity=Decimal("20"),
        purchase_price=Decimal("17000"),
        profit_percentage=Decimal("0.50"),
        created_by="system",
    )
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


def test_movement_entry_updates_existing_inventory_and_creates_history(monkeypatch):
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
    assert inventory.purchase_price == Decimal("106.6666666666666666666666667")
    inventory_repo.save.assert_called_once_with(inventory)


def test_movement_first_entry_creates_inventory_row(monkeypatch):
    product, _ = movement_fixture(quantity=Decimal("0"))
    product_repo = MagicMock()
    inventory_repo = MagicMock()
    movement_repo = MagicMock()
    product_repo.get_by_id.return_value = product
    inventory_repo.get_by_product.return_value = None
    inventory_repo.add.side_effect = lambda value: value
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
        ),
        MagicMock(),
        7,
        user(),
    )

    created_inventory = inventory_repo.add.call_args.args[0]
    assert created_inventory.quantity == Decimal("5")
    assert result.balance_before == Decimal("0")
    assert result.balance_after == Decimal("5")


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


def test_movement_validates_origin_product_and_inactive_product(monkeypatch):
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


def test_inventory_catalog_controllers_delegate(monkeypatch):
    sentinel = object()
    service_calls = []

    def capture(name):
        def _service(*args):
            service_calls.append((name, args))
            return sentinel

        return _service

    monkeypatch.setattr(catalog_controller, "create_inventory_type", capture("create_type"))
    monkeypatch.setattr(catalog_controller, "list_inventory_types", capture("list_types"))
    monkeypatch.setattr(catalog_controller, "update_inventory_type", capture("update_type"))
    monkeypatch.setattr(catalog_controller, "create_product", capture("create_product"))
    monkeypatch.setattr(catalog_controller, "list_products", capture("list_products"))
    monkeypatch.setattr(catalog_controller, "update_product", capture("update_product"))

    db = MagicMock()
    current_user = MagicMock()
    data = MagicMock()

    assert catalog_controller.create_type(data, db, 7, current_user) is sentinel
    assert catalog_controller.list_types(db, 7, True) is sentinel
    assert catalog_controller.update_type(1, data, db, 7, current_user) is sentinel
    assert catalog_controller.create_product_item(data, db, 7, current_user) is sentinel
    assert catalog_controller.list_product_items(db, 7, False) is sentinel
    assert catalog_controller.update_product_item(2, data, db, 7, current_user) is sentinel
    assert [call[0] for call in service_calls] == [
        "create_type", "list_types", "update_type", "create_product", "list_products", "update_product"
    ]


def test_inventory_and_movement_controllers_delegate(monkeypatch):
    sentinel = object()
    db = MagicMock()
    current_user = MagicMock()
    data = MagicMock()
    movement_id = uuid4()

    monkeypatch.setattr(inventory_controller, "list_inventory", lambda *args: sentinel)
    monkeypatch.setattr(inventory_controller, "get_inventory", lambda *args: sentinel)
    assert inventory_controller.list_inventory_items(db, 7) is sentinel
    assert inventory_controller.get_inventory_item(1, db, 7) is sentinel

    monkeypatch.setattr(movement_controller, "create_inventory_movement", lambda *args: sentinel)
    monkeypatch.setattr(movement_controller, "list_inventory_movements", lambda *args, **kwargs: sentinel)
    monkeypatch.setattr(movement_controller, "get_inventory_movement", lambda *args: sentinel)
    assert movement_controller.create_movement(data, db, 7, current_user) is sentinel
    assert movement_controller.list_movements(1, db, 7, limit=20, offset=5) is sentinel
    assert movement_controller.get_movement(movement_id, db, 7) is sentinel


def test_inventory_routes_delegate(monkeypatch):
    sentinel = object()
    db = MagicMock()
    current_user = MagicMock()
    user_tenant = SimpleNamespace(tenant_id=7)
    data = MagicMock()
    movement_id = uuid4()

    monkeypatch.setattr(inventory_routes, "list_types", lambda *args: sentinel)
    monkeypatch.setattr(inventory_routes, "create_type", lambda *args: sentinel)
    monkeypatch.setattr(inventory_routes, "update_type", lambda *args: sentinel)
    monkeypatch.setattr(inventory_routes, "list_product_items", lambda *args: sentinel)
    monkeypatch.setattr(inventory_routes, "create_product_item", lambda *args: sentinel)
    monkeypatch.setattr(inventory_routes, "update_product_item", lambda *args: sentinel)
    monkeypatch.setattr(inventory_routes, "list_inventory_items", lambda *args: sentinel)
    monkeypatch.setattr(inventory_routes, "get_inventory_item", lambda *args: sentinel)
    monkeypatch.setattr(inventory_routes, "create_movement", lambda *args: sentinel)
    monkeypatch.setattr(inventory_routes, "list_movements", lambda *args, **kwargs: sentinel)
    monkeypatch.setattr(inventory_routes, "get_movement", lambda *args: sentinel)

    async def run():
        return [
            await inventory_routes.list_inventory_types_route(True, db, user_tenant),
            await inventory_routes.create_inventory_type_route(data, db, current_user, user_tenant),
            await inventory_routes.update_inventory_type_route(1, data, db, current_user, user_tenant),
            await inventory_routes.list_products_route(False, db, user_tenant),
            await inventory_routes.create_product_route(data, db, current_user, user_tenant),
            await inventory_routes.update_product_route(2, data, db, current_user, user_tenant),
            await inventory_routes.list_inventory_route(db, user_tenant),
            await inventory_routes.get_inventory_route(3, db, user_tenant),
            await inventory_routes.create_inventory_movement_route(data, db, current_user, user_tenant),
            await inventory_routes.list_inventory_movements_route(4, 25, 5, db, user_tenant),
            await inventory_routes.get_inventory_movement_route(movement_id, db, user_tenant),
        ]

    assert asyncio.run(run()) == [sentinel] * 11
