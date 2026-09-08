from unittest.mock import MagicMock
from uuid import uuid4

from UsersAPI.domains.inventory.repositories import (
    InventoryMovementRepository,
    InventoryRepository,
    InventoryTypeRepository,
    ProductRepository,
)


def repository_fixture():
    db = MagicMock()
    query = MagicMock()
    db.query.return_value = query
    query.filter.return_value = query
    query.order_by.return_value = query
    query.offset.return_value = query
    query.limit.return_value = query
    return db, query


def test_inventory_type_repository_methods():
    db, query = repository_fixture()
    entity = MagicMock()
    query.first.return_value = entity
    query.all.return_value = [entity]
    repository = InventoryTypeRepository(db)

    assert repository.add(entity) is entity
    assert repository.get_by_id(7, 1) is entity
    assert repository.get_by_code(7, "A") is entity
    assert repository.list(7) == [entity]
    assert repository.list(7, active_only=True) == [entity]
    assert repository.save(entity) is entity
    assert db.add.call_count == 2
    assert db.flush.call_count == 2


def test_product_repository_methods():
    db, query = repository_fixture()
    entity = MagicMock()
    query.first.return_value = entity
    query.all.return_value = [entity]
    repository = ProductRepository(db)

    assert repository.add(entity) is entity
    assert repository.get_by_id(7, 1) is entity
    assert repository.get_by_code(7, "A") is entity
    assert repository.list(7) == [entity]
    assert repository.list(7, active_only=True) == [entity]
    assert repository.save(entity) is entity
    assert db.add.call_count == 2
    assert db.flush.call_count == 2


def test_inventory_repository_methods_and_lock():
    db, query = repository_fixture()
    entity = MagicMock()
    query.first.return_value = entity
    query.all.return_value = [entity]
    query.with_for_update.return_value = query
    repository = InventoryRepository(db)

    assert repository.get_by_product(7, 1) is entity
    assert repository.get_by_product(7, 1, lock=True) is entity
    assert repository.list(7) == [entity]
    assert repository.add(entity) is entity
    assert repository.save(entity) is entity
    query.with_for_update.assert_called_once_with()
    assert db.add.call_count == 2
    assert db.flush.call_count == 2


def test_movement_repository_methods():
    db, query = repository_fixture()
    entity = MagicMock()
    query.first.return_value = entity
    query.all.return_value = [entity]
    repository = InventoryMovementRepository(db)
    movement_id = uuid4()

    assert repository.add(entity) is entity
    assert repository.get_by_id(7, movement_id) is entity
    assert repository.list_by_product(7, 1) == [entity]
    assert repository.list_by_product(7, 1, limit=10, offset=2) == [entity]
    assert db.add.call_count == 1
    assert db.flush.call_count == 1
