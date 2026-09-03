from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from UsersAPI.services import role_permission_service as service


def _chain(result):
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = result
    return q


def _db(*results):
    db = MagicMock()
    db.query.side_effect = [_chain(r) for r in results]
    return db


def test_assign_permission_success(monkeypatch):
    db = _db(SimpleNamespace(code="ADMIN"), SimpleNamespace(code="USER_READ"))
    repo = MagicMock()
    created = SimpleNamespace(id=10)
    repo.get_by_role_permission.return_value = None
    repo.add.return_value = created
    monkeypatch.setattr(service, "RolePermissionRepository", lambda _: repo)

    assert service.assign_permission_to_role(1, 2, 3, db) is created
    repo.add.assert_called_once()


def test_assign_permission_missing_role(monkeypatch):
    db = _db(None)
    monkeypatch.setattr(service, "RolePermissionRepository", lambda _: MagicMock())
    with pytest.raises(HTTPException) as exc:
        service.assign_permission_to_role(1, 2, 3, db)
    assert exc.value.status_code == 404


def test_assign_permission_missing_permission(monkeypatch):
    db = _db(SimpleNamespace(code="ADMIN"), None)
    monkeypatch.setattr(service, "RolePermissionRepository", lambda _: MagicMock())
    with pytest.raises(HTTPException) as exc:
        service.assign_permission_to_role(1, 2, 3, db)
    assert exc.value.status_code == 404


def test_assign_permission_duplicate(monkeypatch):
    db = _db(SimpleNamespace(code="ADMIN"), SimpleNamespace(code="READ"))
    repo = MagicMock()
    repo.get_by_role_permission.return_value = SimpleNamespace(id=5)
    monkeypatch.setattr(service, "RolePermissionRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc:
        service.assign_permission_to_role(1, 2, 3, db)
    assert exc.value.status_code == 400


@pytest.mark.parametrize(
    "error,status_code",
    [
        (IntegrityError("x", {}, Exception()), 400),
        (RuntimeError("x"), 500),
    ],
)
def test_assign_permission_errors(monkeypatch, error, status_code):
    db = _db(SimpleNamespace(code="ADMIN"), SimpleNamespace(code="READ"))
    repo = MagicMock()
    repo.get_by_role_permission.return_value = None
    repo.add.side_effect = error
    monkeypatch.setattr(service, "RolePermissionRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc:
        service.assign_permission_to_role(1, 2, 3, db)
    assert exc.value.status_code == status_code
    db.rollback.assert_called_once()


def test_list_role_permissions_success(monkeypatch):
    db = _db(SimpleNamespace(id=1))
    repo = MagicMock()
    permissions = [SimpleNamespace(id=2)]
    repo.get_permissions_by_role.return_value = permissions
    monkeypatch.setattr(service, "RolePermissionRepository", lambda _: repo)
    assert service.list_role_permissions(1, 3, db) == permissions


def test_list_role_permissions_missing_role(monkeypatch):
    db = _db(None)
    monkeypatch.setattr(service, "RolePermissionRepository", lambda _: MagicMock())
    with pytest.raises(HTTPException) as exc:
        service.list_role_permissions(1, 3, db)
    assert exc.value.status_code == 404


def test_remove_permission_success(monkeypatch):
    db = _db(SimpleNamespace(id=1))
    relation = SimpleNamespace(id=7, role_id=1, permission_id=2)
    repo = MagicMock()
    repo.get_by_id.return_value = relation
    monkeypatch.setattr(service, "RolePermissionRepository", lambda _: repo)
    result = service.remove_permission_from_role(7, 3, db)
    assert result["id"] == 7
    repo.delete.assert_called_once_with(relation)


def test_remove_permission_missing_relation(monkeypatch):
    db = MagicMock()
    repo = MagicMock()
    repo.get_by_id.return_value = None
    monkeypatch.setattr(service, "RolePermissionRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc:
        service.remove_permission_from_role(7, 3, db)
    assert exc.value.status_code == 404


def test_remove_permission_wrong_tenant(monkeypatch):
    db = _db(None)
    relation = SimpleNamespace(id=7, role_id=1, permission_id=2)
    repo = MagicMock()
    repo.get_by_id.return_value = relation
    monkeypatch.setattr(service, "RolePermissionRepository", lambda _: repo)
    with pytest.raises(HTTPException) as exc:
        service.remove_permission_from_role(7, 3, db)
    assert exc.value.status_code == 404
