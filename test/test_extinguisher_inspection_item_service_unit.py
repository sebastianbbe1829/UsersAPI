from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from UsersAPI.services import extinguisher_inspection_item_service as service


def _datos(code="it01", name="Item", display_order=1):
    return SimpleNamespace(code=code, name=name, display_order=display_order)


def _update(**values):
    return SimpleNamespace(model_dump=lambda exclude_unset=True: values)


def test_list_inspection_items(monkeypatch):
    repo = MagicMock(); repo.get_all.return_value = [1]
    monkeypatch.setattr(service, "ExtinguisherInspectionItemRepository", lambda _: repo)
    assert service.list_inspection_items(MagicMock()) == [1]
    repo.get_all.assert_called_once_with(include_inactive=True)


def test_get_inspection_item_success(monkeypatch):
    repo = MagicMock(); item = SimpleNamespace(id=1); repo.get_by_id.return_value = item
    monkeypatch.setattr(service, "ExtinguisherInspectionItemRepository", lambda _: repo)
    assert service.get_inspection_item(1, MagicMock()) is item


def test_get_inspection_item_missing(monkeypatch):
    repo = MagicMock(); repo.get_by_id.return_value = None
    monkeypatch.setattr(service, "ExtinguisherInspectionItemRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc: service.get_inspection_item(1, MagicMock())
    assert exc.value.status_code == 404


def test_create_success(monkeypatch):
    db = MagicMock(); repo = MagicMock(); repo.get_by_code.return_value = None
    monkeypatch.setattr(service, "ExtinguisherInspectionItemRepository", lambda _: repo)
    item = service.create_inspection_item(_datos(" ab1 ", " Item ", 3), db)
    assert item.code == "AB1" and item.name == "Item" and item.active is True
    db.refresh.assert_called_once_with(item)

@pytest.mark.parametrize("datos", [_datos(" ", "X"), _datos("X", " ")])
def test_create_rejects_blank(datos, monkeypatch):
    repo = MagicMock(); monkeypatch.setattr(service, "ExtinguisherInspectionItemRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc: service.create_inspection_item(datos, MagicMock())
    assert exc.value.status_code == 400


def test_create_duplicate(monkeypatch):
    repo = MagicMock(); repo.get_by_code.return_value = object()
    monkeypatch.setattr(service, "ExtinguisherInspectionItemRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc: service.create_inspection_item(_datos(), MagicMock())
    assert exc.value.status_code == 409


def test_create_integrity_error(monkeypatch):
    db = MagicMock(); repo = MagicMock(); repo.get_by_code.return_value = None
    repo.add.side_effect = IntegrityError("insert", {}, Exception())
    monkeypatch.setattr(service, "ExtinguisherInspectionItemRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc: service.create_inspection_item(_datos(), db)
    assert exc.value.status_code == 409; db.rollback.assert_called_once()


def test_update_success(monkeypatch):
    db = MagicMock(); item = SimpleNamespace(id=1, code="OLD", name="Old")
    repo = MagicMock(); repo.get_by_id.return_value = item; repo.get_by_code.return_value = None
    monkeypatch.setattr(service, "ExtinguisherInspectionItemRepository", lambda _: repo)
    result = service.update_inspection_item(1, _update(code=" new ", name=" Name ", display_order=2), db)
    assert result.code == "NEW" and result.name == "Name" and result.display_order == 2
    db.refresh.assert_called_once_with(item)

@pytest.mark.parametrize("values", [{}, {"code":" "}, {"name":" "}])
def test_update_rejects_invalid_values(values, monkeypatch):
    item = SimpleNamespace(id=1, code="A", name="A")
    repo = MagicMock(); repo.get_by_id.return_value = item; repo.get_by_code.return_value = None
    monkeypatch.setattr(service, "ExtinguisherInspectionItemRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc: service.update_inspection_item(1, _update(**values), MagicMock())
    assert exc.value.status_code == 400


def test_update_duplicate_code(monkeypatch):
    item = SimpleNamespace(id=1); repo = MagicMock(); repo.get_by_id.return_value = item; repo.get_by_code.return_value = SimpleNamespace(id=2)
    monkeypatch.setattr(service, "ExtinguisherInspectionItemRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc: service.update_inspection_item(1, _update(code="B"), MagicMock())
    assert exc.value.status_code == 409


def test_update_missing(monkeypatch):
    repo = MagicMock(); repo.get_by_id.return_value = None
    monkeypatch.setattr(service, "ExtinguisherInspectionItemRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc: service.update_inspection_item(1, _update(name="X"), MagicMock())
    assert exc.value.status_code == 404


def test_update_integrity_error(monkeypatch):
    db = MagicMock(); item = SimpleNamespace(id=1, code="A", name="A")
    repo = MagicMock(); repo.get_by_id.return_value = item; repo.get_by_code.return_value = None
    repo.update.side_effect = IntegrityError("update", {}, Exception())
    monkeypatch.setattr(service, "ExtinguisherInspectionItemRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc: service.update_inspection_item(1, _update(name="B"), db)
    assert exc.value.status_code == 409; db.rollback.assert_called_once()


def test_delete_success(monkeypatch):
    item = SimpleNamespace(id=1, active=True); repo = MagicMock(); repo.get_by_id.return_value = item
    monkeypatch.setattr(service, "ExtinguisherInspectionItemRepository", lambda _: repo)
    result = service.delete_inspection_item(1, MagicMock())
    assert result is item and item.active is False

@pytest.mark.parametrize("item", [None, SimpleNamespace(active=False)])
def test_delete_rejects_missing_or_inactive(item, monkeypatch):
    repo = MagicMock(); repo.get_by_id.return_value = item
    monkeypatch.setattr(service, "ExtinguisherInspectionItemRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc: service.delete_inspection_item(1, MagicMock())
    assert exc.value.status_code in (400, 404)
