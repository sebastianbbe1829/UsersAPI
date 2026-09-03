from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from UsersAPI.services import user_read_service as service


def _user(dni="123", name="User", user_id=1):
    return SimpleNamespace(dni=dni, name=name, id=user_id)


def _link(email="user@example.com", phone="3001234567", status=1):
    return SimpleNamespace(email=email, phone=phone, status=status)


def test_list_users_without_status_filter(monkeypatch):
    repository = MagicMock()
    repository.get_all_by_tenant.return_value = [_user()]
    links = MagicMock()
    links.get_by_user_and_tenant.return_value = _link()
    monkeypatch.setattr(service, "UserRepository", lambda db: repository)
    monkeypatch.setattr(service, "UserTenantRepository", lambda db: links)

    result = service.list_users(MagicMock(), 5)

    assert result == [{
        "dni": "123",
        "name": "User",
        "email": "user@example.com",
        "phone": "3001234567",
        "status": 1,
        "id": 1,
    }]
    repository.get_all_by_tenant.assert_called_once_with(5, None)


def test_list_users_with_status_filter_and_multiple_users(monkeypatch):
    repository = MagicMock()
    repository.get_all_by_tenant.return_value = [_user(), _user("456", "Other", 2)]
    links = MagicMock()
    links.get_by_user_and_tenant.side_effect = [_link(), _link("other@example.com")]
    monkeypatch.setattr(service, "UserRepository", lambda db: repository)
    monkeypatch.setattr(service, "UserTenantRepository", lambda db: links)

    result = service.list_users(MagicMock(), 5, 1)

    assert [item["dni"] for item in result] == ["123", "456"]
    repository.get_all_by_tenant.assert_called_once_with(5, 1)
    assert links.get_by_user_and_tenant.call_count == 2


def test_list_users_raises_when_user_has_no_tenant_link(monkeypatch):
    repository = MagicMock()
    repository.get_all_by_tenant.return_value = [_user()]
    links = MagicMock()
    links.get_by_user_and_tenant.return_value = None
    monkeypatch.setattr(service, "UserRepository", lambda db: repository)
    monkeypatch.setattr(service, "UserTenantRepository", lambda db: links)

    with pytest.raises(HTTPException) as exc:
        service.list_users(MagicMock(), 5)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Usuario no pertenece al tenant"


def test_list_users_empty(monkeypatch):
    repository = MagicMock()
    repository.get_all_by_tenant.return_value = []
    links = MagicMock()
    monkeypatch.setattr(service, "UserRepository", lambda db: repository)
    monkeypatch.setattr(service, "UserTenantRepository", lambda db: links)

    assert service.list_users(MagicMock(), 5) == []
    links.get_by_user_and_tenant.assert_not_called()


def test_get_user_success(monkeypatch):
    repository = MagicMock()
    user = _user()
    repository.get_by_dni_in_tenant.return_value = user
    links = MagicMock()
    links.get_by_user_and_tenant.return_value = _link()
    monkeypatch.setattr(service, "UserRepository", lambda db: repository)
    monkeypatch.setattr(service, "UserTenantRepository", lambda db: links)

    result = service.get_user("123", MagicMock(), 5)

    assert result["dni"] == "123"
    assert result["email"] == "user@example.com"
    repository.get_by_dni_in_tenant.assert_called_once_with("123", 5)
    links.get_by_user_and_tenant.assert_called_once_with(1, 5)


def test_get_user_not_found(monkeypatch):
    repository = MagicMock()
    repository.get_by_dni_in_tenant.return_value = None
    links = MagicMock()
    monkeypatch.setattr(service, "UserRepository", lambda db: repository)
    monkeypatch.setattr(service, "UserTenantRepository", lambda db: links)

    with pytest.raises(HTTPException) as exc:
        service.get_user("999", MagicMock(), 5)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Usuario no encontrado"
    links.get_by_user_and_tenant.assert_not_called()


def test_get_user_not_in_tenant(monkeypatch):
    repository = MagicMock()
    repository.get_by_dni_in_tenant.return_value = _user()
    links = MagicMock()
    links.get_by_user_and_tenant.return_value = None
    monkeypatch.setattr(service, "UserRepository", lambda db: repository)
    monkeypatch.setattr(service, "UserTenantRepository", lambda db: links)

    with pytest.raises(HTTPException) as exc:
        service.get_user("123", MagicMock(), 5)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Usuario no pertenece al tenant"
