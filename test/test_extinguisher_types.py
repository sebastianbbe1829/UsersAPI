from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from UsersAPI.schemas.extinguisher_type import ExtinguisherTypeCreate, ExtinguisherTypeUpdate
from UsersAPI.services import extinguisher_type_service


class FakeSession:
    def __init__(self):
        self.refresh_called = False

    def refresh(self, instance):
        self.refresh_called = True


class FakeRepository:
    def __init__(self, db):
        self.item = None
        self.items_by_code = {}

    def get_by_code(self, code):
        return self.items_by_code.get(code)

    def get_by_id(self, type_id, include_inactive=False):
        return self.item

    def add(self, item):
        item.id = 1
        self.item = item
        self.items_by_code[item.code] = item

    def update(self, item):
        self.item = item
        self.items_by_code[item.code] = item


def test_create_type_normalizes_code_and_name():
    db = FakeSession()
    repo = FakeRepository(db)
    datos = ExtinguisherTypeCreate(code=" co2 ", name=" Dióxido de carbono ")

    with patch.object(extinguisher_type_service, "ExtinguisherTypeRepository", return_value=repo):
        result = extinguisher_type_service.create_extinguisher_type(datos, db)

    assert result.id == 1
    assert result.code == "CO2"
    assert result.name == "Dióxido de carbono"
    assert result.active is True
    assert db.refresh_called


def test_create_type_rejects_duplicate_code():
    db = FakeSession()
    repo = FakeRepository(db)
    repo.items_by_code["CO2"] = SimpleNamespace(id=1, code="CO2")
    datos = ExtinguisherTypeCreate(code="co2", name="Otro nombre")

    with patch.object(extinguisher_type_service, "ExtinguisherTypeRepository", return_value=repo):
        with pytest.raises(HTTPException) as exc_info:
            extinguisher_type_service.create_extinguisher_type(datos, db)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "El tipo de extintor ya existe"


def test_update_type_changes_fields_and_sets_updated_at():
    db = FakeSession()
    existing = SimpleNamespace(
        id=1,
        code="CO2",
        name="Dióxido de carbono",
        active=True,
        updated_at=None,
    )
    repo = FakeRepository(db)
    repo.item = existing
    repo.items_by_code["CO2"] = existing
    datos = ExtinguisherTypeUpdate(code=" co2_new ", name=" CO2 nuevo ")

    with patch.object(extinguisher_type_service, "ExtinguisherTypeRepository", return_value=repo):
        result = extinguisher_type_service.update_extinguisher_type(1, datos, db)

    assert result.code == "CO2_NEW"
    assert result.name == "CO2 nuevo"
    assert isinstance(result.updated_at, datetime)
    assert db.refresh_called


def test_update_type_rejects_duplicate_code():
    db = FakeSession()
    existing = SimpleNamespace(id=1, code="CO2", name="CO2", active=True, updated_at=None)
    other = SimpleNamespace(id=2, code="AGUA", name="Agua", active=True, updated_at=None)
    repo = FakeRepository(db)
    repo.item = existing
    repo.items_by_code["CO2"] = existing
    repo.items_by_code["AGUA"] = other

    with patch.object(extinguisher_type_service, "ExtinguisherTypeRepository", return_value=repo):
        with pytest.raises(HTTPException) as exc_info:
            extinguisher_type_service.update_extinguisher_type(
                1, ExtinguisherTypeUpdate(code="AGUA"), db
            )

    assert exc_info.value.status_code == 409


def test_delete_type_is_soft_delete():
    db = FakeSession()
    existing = SimpleNamespace(id=1, code="CO2", name="CO2", active=True, updated_at=None)
    repo = FakeRepository(db)
    repo.item = existing

    with patch.object(extinguisher_type_service, "ExtinguisherTypeRepository", return_value=repo):
        result = extinguisher_type_service.delete_extinguisher_type(1, db)

    assert result.active is False
    assert isinstance(result.updated_at, datetime)


def test_delete_inactive_type_is_rejected():
    db = FakeSession()
    existing = SimpleNamespace(id=1, code="CO2", name="CO2", active=False, updated_at=None)
    repo = FakeRepository(db)
    repo.item = existing

    with patch.object(extinguisher_type_service, "ExtinguisherTypeRepository", return_value=repo):
        with pytest.raises(HTTPException) as exc_info:
            extinguisher_type_service.delete_extinguisher_type(1, db)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "El tipo de extintor ya está inactivo"
