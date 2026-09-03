from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from UsersAPI.services import super_tenant_service as service


def _super(active=True, superuser=True, email="super@test.com"):
    return SimpleNamespace(is_active=active, is_superuser=superuser, email=email)


def test_require_super_user_success():
    user = _super()
    assert service.require_super_user(user) is user


@pytest.mark.parametrize(
    "user",
    [SimpleNamespace(), _super(active=False), _super(superuser=False)],
)
def test_require_super_user_rejects(user):
    with pytest.raises(HTTPException) as exc:
        service.require_super_user(user)
    assert exc.value.status_code == 403


def test_list_all_tenants(monkeypatch):
    db = MagicMock()
    repo = MagicMock()
    tenants = [SimpleNamespace(id=1)]
    repo.get_all.return_value = tenants
    monkeypatch.setattr(service, "TenantRepository", lambda _: repo)
    assert service.list_all_tenants(db) == tenants


def test_get_any_tenant_success(monkeypatch):
    db = MagicMock()
    tenant = SimpleNamespace(id=1)
    repo = MagicMock()
    repo.get_by_id.return_value = tenant
    monkeypatch.setattr(service, "TenantRepository", lambda _: repo)
    assert service.get_any_tenant(1, db) is tenant


def test_get_any_tenant_missing(monkeypatch):
    db = MagicMock()
    repo = MagicMock()
    repo.get_by_id.return_value = None
    monkeypatch.setattr(service, "TenantRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc:
        service.get_any_tenant(1, db)
    assert exc.value.status_code == 404


def test_provision_tenant_delegates(monkeypatch):
    db = MagicMock()
    datos = SimpleNamespace(
        tenant_name="Acme",
        tenant_slug="acme",
        admin_dni="1",
        admin_name="Admin",
        admin_email="admin@acme.com",
        admin_password="secret",
        admin_phone="300",
    )
    expected = SimpleNamespace(id=1)
    bootstrap = MagicMock(return_value=expected)
    monkeypatch.setattr(service, "bootstrapTenant", bootstrap)
    assert service.provision_tenant(datos, db) is expected
    bootstrap.assert_called_once()


def test_update_any_tenant_success(monkeypatch):
    db = MagicMock()
    tenant = SimpleNamespace(id=1, name="Old", slug="old", status=1)
    datos = SimpleNamespace(name=" New ", slug=" NEW-SLUG ", status=0)
    repo = MagicMock()
    repo.get_by_id.return_value = tenant
    repo.get_by_name.return_value = None
    repo.get_by_slug.return_value = None
    repo.update.return_value = tenant
    monkeypatch.setattr(service, "TenantRepository", lambda _: repo)
    user = _super()
    result = service.update_any_tenant(1, datos, db, user)
    assert result is tenant
    assert tenant.name == "New"
    assert tenant.slug == "new-slug"
    assert tenant.status == 0
    assert tenant.updated_by == user.email


def test_update_any_tenant_missing(monkeypatch):
    db = MagicMock()
    repo = MagicMock()
    repo.get_by_id.return_value = None
    monkeypatch.setattr(service, "TenantRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc:
        service.update_any_tenant(
            1, SimpleNamespace(name="X", slug=None, status=None), db, _super()
        )
    assert exc.value.status_code == 404


def test_update_any_tenant_requires_field(monkeypatch):
    db = MagicMock()
    repo = MagicMock()
    repo.get_by_id.return_value = SimpleNamespace(id=1)
    monkeypatch.setattr(service, "TenantRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc:
        service.update_any_tenant(
            1, SimpleNamespace(name=None, slug=None, status=None), db, _super()
        )
    assert exc.value.status_code == 400


@pytest.mark.parametrize(
    "datos",
    [
        SimpleNamespace(name="   ", slug=None, status=None),
        SimpleNamespace(name=None, slug="   ", status=None),
    ],
)
def test_update_any_tenant_rejects_blank_fields(monkeypatch, datos):
    db = MagicMock()
    repo = MagicMock()
    repo.get_by_id.return_value = SimpleNamespace(id=1)
    monkeypatch.setattr(service, "TenantRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc:
        service.update_any_tenant(1, datos, db, _super())
    assert exc.value.status_code == 422


def test_update_any_tenant_duplicate_name(monkeypatch):
    db = MagicMock()
    tenant = SimpleNamespace(id=1)
    repo = MagicMock()
    repo.get_by_id.return_value = tenant
    repo.get_by_name.return_value = SimpleNamespace(id=2)
    monkeypatch.setattr(service, "TenantRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc:
        service.update_any_tenant(
            1, SimpleNamespace(name="Acme", slug=None, status=None), db, _super()
        )
    assert exc.value.status_code == 400


def test_update_any_tenant_duplicate_slug(monkeypatch):
    db = MagicMock()
    tenant = SimpleNamespace(id=1)
    repo = MagicMock()
    repo.get_by_id.return_value = tenant
    repo.get_by_name.return_value = None
    repo.get_by_slug.return_value = SimpleNamespace(id=2)
    monkeypatch.setattr(service, "TenantRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc:
        service.update_any_tenant(
            1, SimpleNamespace(name=None, slug="Acme", status=None), db, _super()
        )
    assert exc.value.status_code == 400


def test_update_any_tenant_integrity_error(monkeypatch):
    db = MagicMock()
    tenant = SimpleNamespace(id=1, name="Acme", slug="acme", status=1)
    repo = MagicMock()
    repo.get_by_id.return_value = tenant
    repo.get_by_name.return_value = None
    repo.update.side_effect = IntegrityError("update", {}, Exception())
    monkeypatch.setattr(service, "TenantRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc:
        service.update_any_tenant(
            1,
            SimpleNamespace(name="Acme 2", slug=None, status=None),
            db,
            _super(),
        )
    assert exc.value.status_code == 400
    db.rollback.assert_called_once()
