from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from UsersAPI.services import tenant_service


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def current_user():
    return SimpleNamespace(email="admin@example.com", user_id=10)


def tenant(**kwargs):
    defaults = dict(id=1, name="Acme", slug="acme", status=1)
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_actor_email_returns_user_email():
    user = SimpleNamespace(email="user@example.com")
    assert tenant_service._actor_email(user) == "user@example.com"


def test_actor_email_returns_bootstrap_without_user():
    assert tenant_service._actor_email(None) == "bootstrap"


def test_create_tenant_normalizes_and_creates(db, current_user, monkeypatch):
    repo = MagicMock()
    repo.get_by_name.return_value = None
    repo.get_by_slug.return_value = None
    created = tenant(name="Acme Corp", slug="acme-corp")
    repo.add.return_value = created
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)

    result = tenant_service.create_tenant("  Acme Corp  ", "  Acme-Corp  ", db, current_user)

    assert result is created
    obj = repo.add.call_args.args[0]
    assert obj.name == "Acme Corp"
    assert obj.slug == "acme-corp"
    assert obj.status == 1
    assert obj.created_by == "admin@example.com"


def test_create_tenant_rejects_duplicate_name(db, monkeypatch):
    repo = MagicMock()
    repo.get_by_name.return_value = tenant()
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        tenant_service.create_tenant("Acme", "new-slug", db)

    assert exc.value.status_code == 400
    assert "nombre" in exc.value.detail
    repo.add.assert_not_called()


def test_create_tenant_rejects_duplicate_slug(db, monkeypatch):
    repo = MagicMock()
    repo.get_by_name.return_value = None
    repo.get_by_slug.return_value = tenant()
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        tenant_service.create_tenant("New Name", "acme", db)

    assert exc.value.status_code == 400
    assert "slug" in exc.value.detail
    repo.add.assert_not_called()


def test_create_tenant_integrity_error_rolls_back(db, monkeypatch):
    repo = MagicMock()
    repo.get_by_name.return_value = None
    repo.get_by_slug.return_value = None
    repo.add.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        tenant_service.create_tenant("Acme", "acme", db)

    assert exc.value.status_code == 400
    db.rollback.assert_called_once_with()


def test_create_tenant_unexpected_error_rolls_back(db, monkeypatch):
    repo = MagicMock()
    repo.get_by_name.return_value = None
    repo.get_by_slug.return_value = None
    repo.add.side_effect = RuntimeError("failure")
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        tenant_service.create_tenant("Acme", "acme", db)

    assert exc.value.status_code == 500
    db.rollback.assert_called_once_with()


def test_list_tenants_returns_current_tenant(db, monkeypatch):
    repo = MagicMock()
    obj = tenant()
    repo.get_by_id.return_value = obj
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)

    assert tenant_service.list_tenants(1, db) == [obj]


def test_list_tenants_returns_empty_when_missing_or_status_mismatch(db, monkeypatch):
    repo = MagicMock()
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)

    repo.get_by_id.return_value = None
    assert tenant_service.list_tenants(1, db) == []

    repo.get_by_id.return_value = tenant(status=0)
    assert tenant_service.list_tenants(1, db, status_filter=1) == []


def test_get_tenant_enforces_context(db, monkeypatch):
    with pytest.raises(HTTPException) as exc:
        tenant_service.get_tenant(2, 1, db)
    assert exc.value.status_code == 404

    repo = MagicMock()
    repo.get_by_id.return_value = None
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc:
        tenant_service.get_tenant(1, 1, db)
    assert exc.value.status_code == 404


def test_get_tenant_returns_current_tenant(db, monkeypatch):
    repo = MagicMock()
    obj = tenant()
    repo.get_by_id.return_value = obj
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)
    assert tenant_service.get_tenant(1, 1, db) is obj


def test_update_tenant_rejects_wrong_context(db):
    with pytest.raises(HTTPException) as exc:
        tenant_service.update_tenant(2, 1, "Name", None, db)
    assert exc.value.status_code == 404


def test_update_tenant_rejects_missing_tenant(db, monkeypatch):
    repo = MagicMock()
    repo.get_by_id.return_value = None
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc:
        tenant_service.update_tenant(1, 1, "Name", None, db)
    assert exc.value.status_code == 404


def test_update_tenant_rejects_duplicate_name(db, monkeypatch):
    repo = MagicMock()
    obj = tenant()
    repo.get_by_id.return_value = obj
    repo.get_by_name.return_value = tenant(id=2, name="Other")
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc:
        tenant_service.update_tenant(1, 1, "Other", None, db)
    assert exc.value.status_code == 400


def test_update_tenant_rejects_duplicate_slug(db, monkeypatch):
    repo = MagicMock()
    obj = tenant()
    repo.get_by_id.return_value = obj
    repo.get_by_name.return_value = None
    repo.get_by_slug.return_value = tenant(id=2, slug="other")
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc:
        tenant_service.update_tenant(1, 1, None, "other", db)
    assert exc.value.status_code == 400


def test_update_tenant_normalizes_and_updates(db, current_user, monkeypatch):
    repo = MagicMock()
    obj = tenant()
    repo.get_by_id.return_value = obj
    repo.get_by_name.return_value = None
    repo.get_by_slug.return_value = None
    repo.update.return_value = obj
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)

    result = tenant_service.update_tenant(1, 1, "  New Name ", " NEW-SLUG ", db, current_user)

    assert result is obj
    assert obj.name == "New Name"
    assert obj.slug == "new-slug"
    assert obj.updated_by == "admin@example.com"


def test_update_tenant_integrity_error_rolls_back(db, monkeypatch):
    repo = MagicMock()
    obj = tenant()
    repo.get_by_id.return_value = obj
    repo.update.side_effect = IntegrityError("update", {}, Exception("duplicate"))
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        tenant_service.update_tenant(1, 1, None, None, db)
    assert exc.value.status_code == 400
    db.rollback.assert_called_once_with()


def test_delete_tenant_enforces_context_and_missing(db, monkeypatch):
    with pytest.raises(HTTPException) as exc:
        tenant_service.delete_tenant(2, 1, db)
    assert exc.value.status_code == 404

    repo = MagicMock()
    repo.get_by_id.return_value = None
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc:
        tenant_service.delete_tenant(1, 1, db)
    assert exc.value.status_code == 404


def test_delete_tenant_soft_deletes_and_returns_data(db, monkeypatch):
    repo = MagicMock()
    obj = tenant(status=0)
    repo.get_by_id.return_value = obj
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)

    result = tenant_service.delete_tenant(1, 1, db)

    repo.delete.assert_called_once_with(obj)
    assert result["id"] == 1
    assert result["message"] == "Tenant eliminado correctamente"


def test_list_my_tenants_uses_global_user_id(db, current_user, monkeypatch):
    repo = MagicMock()
    tenants = [tenant(), tenant(id=2, name="Beta", slug="beta")]
    repo.get_by_user_id.return_value = tenants
    monkeypatch.setattr(tenant_service, "TenantRepository", lambda _: repo)

    assert tenant_service.list_my_tenants(db, current_user) == tenants
    repo.get_by_user_id.assert_called_once_with(user_id=10, status_filter=1)
