from unittest.mock import MagicMock

from UsersAPI.repositories.extinguisher_inspection_item_repository import (
    ExtinguisherInspectionItemRepository,
)
from UsersAPI.repositories.extinguisher_inspection_repository import (
    ExtinguisherInspectionRepository,
)
from UsersAPI.repositories.extinguisher_repository import ExtinguisherRepository
from UsersAPI.repositories.extinguisher_type_repository import ExtinguisherTypeRepository


def _query_db():
    query = MagicMock()
    query.filter.return_value = query
    query.options.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.with_for_update.return_value = query
    db = MagicMock()
    db.query.return_value = query
    return db, query


def test_extinguisher_repository_crud_and_filters():
    db, query = _query_db()
    item = object()
    query.all.return_value = [item]
    query.first.return_value = item
    repo = ExtinguisherRepository(db)

    assert repo.add(item) is item
    db.add.assert_called_once_with(item)
    db.flush.assert_called_once()
    db.reset_mock()

    assert repo.get_all_by_tenant(1) == [item]
    assert query.filter.call_count == 2
    assert query.order_by.called
    db.reset_mock()
    query.reset_mock()
    query.filter.return_value = query
    query.all.return_value = [item]
    assert repo.get_all_by_tenant(1, include_inactive=True) == [item]
    assert query.filter.call_count == 1

    db.reset_mock()
    query.reset_mock()
    query.filter.return_value = query
    query.limit.return_value = query
    query.all.return_value = [item]
    assert repo.search_by_tenant(1, "  ABC  ", 5) == [item]
    assert query.options.called
    assert query.limit.call_args.args == (5,)
    assert query.filter.call_count == 2

    query.reset_mock()
    query.filter.return_value = query
    query.first.return_value = item
    assert repo.get_by_id_and_tenant(7, 1) is item
    assert query.filter.call_count == 2
    query.reset_mock()
    query.filter.return_value = query
    assert repo.get_by_id_and_tenant(7, 1, True) is item
    assert query.filter.call_count == 1

    query.reset_mock()
    query.filter.return_value = query
    assert repo.get_by_code_and_tenant("ABC", 1) is item
    assert query.filter.call_count == 2
    query.reset_mock()
    query.filter.return_value = query
    assert repo.get_by_code_and_tenant("ABC", 1, True) is item
    assert query.filter.call_count == 1

    assert repo.update(item) is item
    assert db.add.call_args.args == (item,)
    assert db.flush.called


def test_extinguisher_repository_search_empty_text():
    db, query = _query_db()
    query.all.return_value = []
    assert ExtinguisherRepository(db).search_by_tenant(1, "   ") == []
    assert query.filter.call_count == 1


def test_extinguisher_type_repository_all_paths():
    db, query = _query_db()
    item = object()
    query.all.return_value = [item]
    query.first.return_value = item
    repo = ExtinguisherTypeRepository(db)

    assert repo.get_all() == [item]
    assert query.filter.call_count == 1
    query.reset_mock(); query.filter.return_value = query
    assert repo.get_all(True) == [item]
    assert query.filter.call_count == 0
    query.reset_mock(); query.filter.return_value = query
    assert repo.get_by_id(2) is item
    assert query.filter.call_count == 2
    query.reset_mock(); query.filter.return_value = query
    assert repo.get_by_id(2, True) is item
    assert query.filter.call_count == 1
    query.reset_mock(); query.filter.return_value = query
    assert repo.get_by_code("CO2") is item
    assert query.filter.call_count == 1
    assert repo.add(item) is item
    assert repo.update(item) is item
    assert db.add.call_count == 2
    assert db.flush.call_count == 2


def test_extinguisher_inspection_item_repository_all_paths():
    db, query = _query_db()
    item = object()
    query.all.return_value = [item]
    query.first.return_value = item
    repo = ExtinguisherInspectionItemRepository(db)

    assert repo.get_all() == [item]
    assert query.filter.call_count == 0
    query.reset_mock(); query.filter.return_value = query
    assert repo.get_all(False) == [item]
    assert query.filter.call_count == 1
    query.reset_mock(); query.filter.return_value = query
    assert repo.get_by_id(3) is item
    assert query.filter.call_count == 1
    query.reset_mock(); query.filter.return_value = query
    assert repo.get_by_id(3, False) is item
    assert query.filter.call_count == 2
    query.reset_mock(); query.filter.return_value = query
    assert repo.get_by_code("X") is item
    assert query.filter.call_count == 1
    assert repo.add(item) is item
    assert repo.update(item) is item


def test_extinguisher_inspection_repository_all_paths():
    db, query = _query_db()
    item = object()
    query.first.return_value = item
    query.all.return_value = [item]
    repo = ExtinguisherInspectionRepository(db)

    assert repo.get_extinguisher_for_update(4, 1) is item
    assert query.filter.call_count == 1
    assert query.with_for_update.called
    query.reset_mock(); query.filter.return_value = query
    assert repo.get_by_id_and_tenant(5, 1) is item
    assert query.options.called
    assert query.filter.call_count == 1
    query.reset_mock(); query.filter.return_value = query
    assert repo.get_all_by_tenant(1) == [item]
    assert query.filter.call_count == 1
    query.reset_mock(); query.filter.return_value = query
    assert repo.get_all_by_tenant(1, 4) == [item]
    assert query.filter.call_count == 2
    assert repo.add(item) is item
