from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from UsersAPI.services import user_activation_service as service


def context(*, tenant_id=5, user_id=10, link_user_id=10, link_status=0):
    db = MagicMock()
    result = MagicMock()
    result.scalar.return_value = tenant_id
    db.execute.return_value = result
    user = SimpleNamespace(
        id=user_id,
        dni="12345678",
        name="Test User",
        updated_at=None,
        updated_by=None,
    )
    link = SimpleNamespace(
        id=20,
        user_id=link_user_id,
        email="test@example.com",
        phone="3000000000",
        status=link_status,
        activation_token="token",
        updated_at=None,
        updated_by=None,
    )
    user_repo = MagicMock()
    user_repo.get_by_dni.return_value = user
    tenant_repo = MagicMock()
    tenant_repo.get_by_activation_token.return_value = link
    return db, user, link, user_repo, tenant_repo


def patch_repositories(monkeypatch, user_repo, tenant_repo):
    monkeypatch.setattr(service, "UserRepository", lambda db: user_repo)
    monkeypatch.setattr(service, "UserTenantRepository", lambda db: tenant_repo)
    monkeypatch.setattr(service, "set_rls_tenant", MagicMock())


def test_invalid_token_from_tenant_resolution(monkeypatch):
    db, *_ = context(tenant_id=None)
    with pytest.raises(HTTPException) as exc:
        service.activate_user("12345678", "bad", db)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Token de activación inválido"


def test_user_not_found(monkeypatch):
    db, _, _, user_repo, tenant_repo = context()
    user_repo.get_by_dni.return_value = None
    patch_repositories(monkeypatch, user_repo, tenant_repo)
    with pytest.raises(HTTPException) as exc:
        service.activate_user("12345678", "token", db)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Usuario no encontrado"


def test_activation_link_not_found(monkeypatch):
    db, _, _, user_repo, tenant_repo = context()
    tenant_repo.get_by_activation_token.return_value = None
    patch_repositories(monkeypatch, user_repo, tenant_repo)
    with pytest.raises(HTTPException) as exc:
        service.activate_user("12345678", "token", db)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Token de activación inválido"


def test_token_belongs_to_another_user(monkeypatch):
    db, _, _, user_repo, tenant_repo = context(link_user_id=99)
    patch_repositories(monkeypatch, user_repo, tenant_repo)
    with pytest.raises(HTTPException) as exc:
        service.activate_user("12345678", "token", db)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Token de activación inválido"


@pytest.mark.parametrize(
    ("link_status", "expected_status", "detail"),
    [
        (3, 400, "El usuario se encuentra eliminado"),
        (1, 409, "El usuario ya se encuentra activo"),
    ],
)
def test_activation_rejects_terminal_status(
    monkeypatch, link_status, expected_status, detail
):
    db, _, _, user_repo, tenant_repo = context(link_status=link_status)
    patch_repositories(monkeypatch, user_repo, tenant_repo)
    with pytest.raises(HTTPException) as exc:
        service.activate_user("12345678", "token", db)
    assert exc.value.status_code == expected_status
    assert exc.value.detail == detail


def test_activation_success_updates_user_and_link(monkeypatch):
    db, user, link, user_repo, tenant_repo = context()
    patch_repositories(monkeypatch, user_repo, tenant_repo)
    result = service.activate_user("12345678", "token", db)
    assert result["message"] == "Usuario activado correctamente"
    assert link.status == 1
    assert link.activation_token is None
    assert link.updated_by == "activation"
    assert user.updated_by == "activation"
    tenant_repo.update.assert_called_once_with(link)
    user_repo.update.assert_called_once_with(user)


def test_activation_integrity_error_returns_bad_request(monkeypatch):
    db, _, link, user_repo, tenant_repo = context()
    patch_repositories(monkeypatch, user_repo, tenant_repo)
    tenant_repo.update.side_effect = IntegrityError("UPDATE", {}, Exception("duplicate"))
    with pytest.raises(HTTPException) as exc:
        service.activate_user("12345678", "token", db)
    assert exc.value.status_code == 400
    assert exc.value.detail == "No fue posible activar el usuario"
    assert link.status == 1


def test_activation_unexpected_error_returns_internal_server_error(monkeypatch):
    db, _, _, user_repo, tenant_repo = context()
    patch_repositories(monkeypatch, user_repo, tenant_repo)
    tenant_repo.update.side_effect = RuntimeError("database unavailable")
    with pytest.raises(HTTPException) as exc:
        service.activate_user("12345678", "token", db)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Error interno al activar usuario"
