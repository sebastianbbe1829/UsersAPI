from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from UsersAPI.schemas.extinguisher import ExtinguisherCreate, ExtinguisherUpdate
from UsersAPI.services import extinguisher_service


class FakeSession:
    def __init__(self):
        self.commit_called = False
        self.refresh_called = False

    def commit(self):
        self.commit_called = True

    def refresh(self, instance):
        self.refresh_called = True

    def rollback(self):
        pass


class FakeRepository:
    def __init__(self, db):
        self.db = db
        self.extinguisher = None

    def get_by_code_and_tenant(self, code, tenant_id, include_inactive=False):
        return None

    def get_by_id_and_tenant(self, extinguisher_id, tenant_id, include_inactive=False):
        return self.extinguisher

    def add(self, extinguisher):
        extinguisher.id = 1
        self.extinguisher = extinguisher

    def update(self, extinguisher):
        self.extinguisher = extinguisher


def test_create_extinguisher_does_not_commit():
    db = FakeSession()
    user_tenant = SimpleNamespace(tenant_id=1)
    datos = ExtinguisherCreate(
        code=" ext-001 ",
        extinguisher_type=" POLVO_QUIMICO_SECO ",
        capacity="10 LB",
        location="Área de producción",
        status="active",
    )

    repository = FakeRepository(db)
    with patch.object(extinguisher_service, "ExtinguisherRepository", return_value=repository):
        result = extinguisher_service.create_extinguisher(datos, db, user_tenant)

    assert result.id == 1
    assert result.code == "EXT-001"
    assert result.extinguisher_type == "POLVO_QUIMICO_SECO"
    assert db.refresh_called
    assert not db.commit_called


def test_update_extinguisher_does_not_commit():
    db = FakeSession()
    user_tenant = SimpleNamespace(tenant_id=1)
    existing = SimpleNamespace(
        id=1,
        tenant_id=1,
        code="EXT-001",
        extinguisher_type="POLVO_QUIMICO_SECO",
        capacity="10 LB",
        location="Área de producción",
        status="ACTIVE",
        updated_at=None,
    )

    datos = ExtinguisherUpdate(
        location="Área de producción - Línea 2",
        status="active",
    )

    repository = FakeRepository(db)
    repository.extinguisher = existing

    with patch.object(extinguisher_service, "ExtinguisherRepository", return_value=repository):
        result = extinguisher_service.update_extinguisher(1, datos, db, user_tenant)

    assert result.location == "Área de producción - Línea 2"
    assert result.status == "ACTIVE"
    assert isinstance(result.updated_at, datetime)
    assert db.refresh_called
    assert not db.commit_called


def test_delete_extinguisher_does_not_commit():
    db = FakeSession()
    user_tenant = SimpleNamespace(tenant_id=1)
    existing = SimpleNamespace(id=1, tenant_id=1, active=True, updated_at=None)

    repository = FakeRepository(db)
    repository.extinguisher = existing

    with patch.object(extinguisher_service, "ExtinguisherRepository", return_value=repository):
        result = extinguisher_service.delete_extinguisher(1, db, user_tenant)

    assert existing.active is False
    assert isinstance(existing.updated_at, datetime)
    assert result == {
        "message": "Extintor desactivado correctamente",
        "id": 1,
    }
    assert not db.commit_called
