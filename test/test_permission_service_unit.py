from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from UsersAPI.schemas import PermissionCreate
from UsersAPI.services import permission_service


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def current_user():
    return SimpleNamespace(user=SimpleNamespace(dni="123456"))


def test_list_permission_returns_repository_result(db, monkeypatch):
    permissions = [SimpleNamespace(code="USER_READ")]
    repo = MagicMock()
    repo.get_all_by_permission.return_value = permissions
    monkeypatch.setattr(permission_service, "PermissionRepository", lambda _: repo)

    assert permission_service.list_permission(db) == permissions
    repo.get_all_by_permission.assert_called_once_with()


def test_get_permission_returns_permission(db, monkeypatch):
    permission = SimpleNamespace(code="USER_READ")
    repo = MagicMock()
    repo.get_by_code.return_value = permission
    monkeypatch.setattr(permission_service, "PermissionRepository", lambda _: repo)

    assert permission_service.get_permission("USER_READ", db) is permission


def test_get_permission_raises_404(db, monkeypatch):
    repo = MagicMock()
    repo.get_by_code.return_value = None
    monkeypatch.setattr(permission_service, "PermissionRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        permission_service.get_permission("MISSING", db)

    assert exc.value.status_code == 404


def test_create_permission_normalizes_and_creates(db, current_user, monkeypatch):
    repo = MagicMock()
    repo.get_by_code_any_status.return_value = None
    permission = SimpleNamespace(code="USER_CREATE")
    repo.create.return_value = permission
    monkeypatch.setattr(permission_service, "PermissionRepository", lambda _: repo)

    result = permission_service.create_permission(
        PermissionCreate(code=" user_create ", name="  Crear usuarios  ", description="  desc  "),
        current_user,
        db,
    )

    assert result is permission
    created = repo.create.call_args.args[0]
    assert created.code == "USER_CREATE"
    assert created.name == "Crear usuarios"
    assert created.description == "desc"
    assert created.status == 1
    assert created.created_by == "123456"
    db.commit.assert_called_once_with()
    db.refresh.assert_called_once_with(permission)


def test_create_permission_allows_empty_description_as_none(db, current_user, monkeypatch):
    repo = MagicMock()
    repo.get_by_code_any_status.return_value = None
    repo.create.return_value = SimpleNamespace(code="X")
    monkeypatch.setattr(permission_service, "PermissionRepository", lambda _: repo)

    permission_service.create_permission(
        PermissionCreate(code="x", name="Name", description="   "),
        current_user,
        db,
    )

    assert repo.create.call_args.args[0].description == ""


@pytest.mark.parametrize(
    ("data", "detail"),
    [
        (PermissionCreate(code="   ", name="Name"), "El código del permiso es obligatorio."),
        (PermissionCreate(code="CODE", name="   "), "El nombre del permiso es obligatorio."),
    ],
)
def test_create_permission_validates_required_fields(db, current_user, monkeypatch, data, detail):
    repo = MagicMock()
    monkeypatch.setattr(permission_service, "PermissionRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        permission_service.create_permission(data, current_user, db)

    assert exc.value.status_code == 400
    assert exc.value.detail == detail
    repo.get_by_code_any_status.assert_not_called()


def test_create_permission_rejects_existing_code(db, current_user, monkeypatch):
    repo = MagicMock()
    repo.get_by_code_any_status.return_value = SimpleNamespace(code="USER_READ")
    monkeypatch.setattr(permission_service, "PermissionRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        permission_service.create_permission(
            PermissionCreate(code="user_read", name="Read"), current_user, db
        )

    assert exc.value.status_code == 409
    repo.create.assert_not_called()


def test_create_permission_integrity_error_rolls_back(db, current_user, monkeypatch):
    repo = MagicMock()
    repo.get_by_code_any_status.return_value = None
    repo.create.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
    monkeypatch.setattr(permission_service, "PermissionRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        permission_service.create_permission(
            PermissionCreate(code="X", name="Name"), current_user, db
        )

    assert exc.value.status_code == 409
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_create_permission_unexpected_error_rolls_back(db, current_user, monkeypatch):
    repo = MagicMock()
    repo.get_by_code_any_status.return_value = None
    repo.create.side_effect = RuntimeError("database unavailable")
    monkeypatch.setattr(permission_service, "PermissionRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        permission_service.create_permission(
            PermissionCreate(code="X", name="Name"), current_user, db
        )

    assert exc.value.status_code == 500
    assert exc.value.detail == "No fue posible crear el permiso."
    db.rollback.assert_called_once_with()
