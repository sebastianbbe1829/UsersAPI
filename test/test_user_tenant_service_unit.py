from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from UsersAPI.services import user_tenant_service


@pytest.fixture
def db():
    return MagicMock()


def test_list_user_tenants_returns_association(db, monkeypatch):
    user_repo = MagicMock()
    user_repo.get_by_id_including_deleted.return_value = SimpleNamespace(id=7)
    association = SimpleNamespace(user_id=7, tenant_id=3)
    tenant_repo = MagicMock()
    tenant_repo.get_by_user_and_tenant.return_value = association

    monkeypatch.setattr(user_tenant_service, "UserRepository", lambda _: user_repo)
    monkeypatch.setattr(user_tenant_service, "UserTenantRepository", lambda _: tenant_repo)

    assert user_tenant_service.list_user_tenants(7, 3, db) == [association]
    tenant_repo.get_by_user_and_tenant.assert_called_once_with(user_id=7, tenant_id=3)


def test_list_user_tenants_returns_empty_without_association(db, monkeypatch):
    user_repo = MagicMock()
    user_repo.get_by_id_including_deleted.return_value = SimpleNamespace(id=7)
    tenant_repo = MagicMock()
    tenant_repo.get_by_user_and_tenant.return_value = None

    monkeypatch.setattr(user_tenant_service, "UserRepository", lambda _: user_repo)
    monkeypatch.setattr(user_tenant_service, "UserTenantRepository", lambda _: tenant_repo)

    assert user_tenant_service.list_user_tenants(7, 3, db) == []


def test_list_user_tenants_rejects_unknown_user(db, monkeypatch):
    user_repo = MagicMock()
    user_repo.get_by_id_including_deleted.return_value = None
    tenant_repo = MagicMock()

    monkeypatch.setattr(user_tenant_service, "UserRepository", lambda _: user_repo)
    monkeypatch.setattr(user_tenant_service, "UserTenantRepository", lambda _: tenant_repo)

    with pytest.raises(HTTPException) as exc:
        user_tenant_service.list_user_tenants(99, 3, db)

    assert exc.value.status_code == 404
    assert exc.value.detail == "El usuario no existe"
    tenant_repo.get_by_user_and_tenant.assert_not_called()
