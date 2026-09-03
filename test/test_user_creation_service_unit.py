from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from UsersAPI.schemas import UserCreate
from UsersAPI.services import user_creation_service as service


def user_data():
    return UserCreate(
        dni="12345678",
        name="Test User",
        email="test@example.com",
        phone="3000000000",
        password="secret1",
        status=0,
    )


def test_create_tenant_link_success(monkeypatch):
    repo = MagicMock()
    usuario = SimpleNamespace(id=10, dni="12345678")
    result = SimpleNamespace(id=20)
    repo.add.return_value = result
    monkeypatch.setattr(service, "get_password_hash", lambda value: f"hash:{value}")
    link = service.create_tenant_link(user_data(), usuario, 5, "actor", repo)
    assert link is result
    created = repo.add.call_args.args[0]
    assert created.user_id == 10
    assert created.tenant_id == 5
    assert created.password == "hash:secret1"
    assert created.created_by == "actor"
    assert created.status == 0


@pytest.mark.parametrize(
    "error, expected_status, expected_detail",
    [
        (
            IntegrityError("INSERT", {}, Exception("duplicate")),
            400,
            "El DNI o el email ya están registrados en este tenant",
        ),
        (RuntimeError("db"), 500, "Error interno al crear usuario"),
    ],
)
def test_create_tenant_link_errors(monkeypatch, error, expected_status, expected_detail):
    repo = MagicMock()
    repo.add.side_effect = error
    usuario = SimpleNamespace(id=10, dni="12345678")
    monkeypatch.setattr(service, "get_password_hash", lambda value: "hash")
    with pytest.raises(HTTPException) as exc:
        service.create_tenant_link(user_data(), usuario, 5, "actor", repo)
    assert exc.value.status_code == expected_status
    assert exc.value.detail == expected_detail


def test_reactivate_user_updates_both_entities(monkeypatch):
    user = user_data()
    usuario = SimpleNamespace(
        id=10,
        dni="12345678",
        name="Old",
        updated_at=None,
        updated_by=None,
    )
    link = SimpleNamespace(
        id=20,
        email="old@example.com",
        password="old",
        phone="1",
        activation_token=None,
        status=3,
        updated_at=None,
        updated_by=None,
    )
    user_repo = MagicMock()
    tenant_repo = MagicMock()
    monkeypatch.setattr(service, "get_password_hash", lambda value: f"hash:{value}")
    result = service.reactivate_user(
        user, usuario, link, 5, "actor", user_repo, tenant_repo
    )
    assert result is link
    assert usuario.name == "Test User"
    assert link.email == "test@example.com"
    assert link.password == "hash:secret1"
    assert link.status == 0
    assert link.activation_token
    assert link.updated_by == "actor"
    user_repo.update.assert_called_once_with(usuario)
    tenant_repo.update.assert_called_once_with(link)


def test_reactivate_user_integrity_error(monkeypatch):
    user = user_data()
    usuario = SimpleNamespace(id=10, dni="12345678", name="Old")
    link = SimpleNamespace(id=20)
    user_repo = MagicMock()
    user_repo.update.side_effect = IntegrityError("UPDATE", {}, Exception("duplicate"))
    tenant_repo = MagicMock()
    with pytest.raises(HTTPException) as exc:
        service.reactivate_user(user, usuario, link, 5, "actor", user_repo, tenant_repo)
    assert exc.value.status_code == 400


def test_reactivate_user_unexpected_error(monkeypatch):
    user = user_data()
    usuario = SimpleNamespace(id=10, dni="12345678", name="Old")
    link = SimpleNamespace(id=20)
    user_repo = MagicMock()
    user_repo.update.side_effect = RuntimeError("db")
    tenant_repo = MagicMock()
    with pytest.raises(HTTPException) as exc:
        service.reactivate_user(user, usuario, link, 5, "actor", user_repo, tenant_repo)
    assert exc.value.status_code == 500


def test_create_global_user_success(monkeypatch):
    repo = MagicMock()
    usuario = SimpleNamespace(id=10)
    repo.add.return_value = usuario
    result = service.create_global_user(user_data(), 5, "actor", repo)
    assert result is usuario
    created = repo.add.call_args.args[0]
    assert created.dni == "12345678"
    assert created.name == "Test User"
    assert created.created_by == "actor"


@pytest.mark.parametrize(
    "error, expected_status, expected_detail",
    [
        (
            IntegrityError("INSERT", {}, Exception("duplicate")),
            400,
            "No fue posible crear el usuario",
        ),
        (RuntimeError("db"), 500, "Error interno al crear usuario"),
    ],
)
def test_create_global_user_errors(error, expected_status, expected_detail):
    repo = MagicMock()
    repo.add.side_effect = error
    with pytest.raises(HTTPException) as exc:
        service.create_global_user(user_data(), 5, "actor", repo)
    assert exc.value.status_code == expected_status
    assert exc.value.detail == expected_detail


def test_create_user_requires_tenant_context(monkeypatch):
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        service.create_user(user_data(), db)
    assert exc.value.status_code == 409
    assert exc.value.detail == "No existe un tenant asociado al contexto actual"


def test_create_user_requires_existing_tenant(monkeypatch):
    db = MagicMock()
    tenant_repo = MagicMock()
    tenant_repo.get_by_id.return_value = None
    monkeypatch.setattr(service, "TenantRepository", lambda db: tenant_repo)
    monkeypatch.setattr(service, "UserRepository", lambda db: MagicMock())
    monkeypatch.setattr(service, "UserTenantRepository", lambda db: MagicMock())
    context = SimpleNamespace(tenant_id=5)
    with pytest.raises(HTTPException) as exc:
        service.create_user(user_data(), db, user_tenant=context)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Tenant no encontrado"


def test_create_user_rejects_existing_active_link(monkeypatch):
    db = MagicMock()
    tenant_repo = MagicMock()
    tenant_repo.get_by_id.return_value = SimpleNamespace(
        id=5, slug="tenant", name="Tenant"
    )
    user_repo = MagicMock()
    user_repo.get_by_dni.return_value = SimpleNamespace(id=10, dni="12345678")
    tenant_link_repo = MagicMock()
    tenant_link_repo.get_by_user_and_tenant_including_deleted.return_value = (
        SimpleNamespace(status=1)
    )
    monkeypatch.setattr(service, "TenantRepository", lambda db: tenant_repo)
    monkeypatch.setattr(service, "UserRepository", lambda db: user_repo)
    monkeypatch.setattr(service, "UserTenantRepository", lambda db: tenant_link_repo)
    context = SimpleNamespace(tenant_id=5)
    with pytest.raises(HTTPException) as exc:
        service.create_user(user_data(), db, user_tenant=context)
    assert exc.value.status_code == 409
    assert exc.value.detail == "El usuario ya pertenece al tenant"
