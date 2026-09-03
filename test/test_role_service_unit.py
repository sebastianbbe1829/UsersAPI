from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from UsersAPI.services import role_service


@pytest.fixture
def db():
    return MagicMock()


def user(email="admin@test.com"):
    return SimpleNamespace(email=email)


def role(**kwargs):
    values = dict(id=1, tenant_id=10, code="ADMIN", name="Admin", description=None, status=1)
    values.update(kwargs)
    return SimpleNamespace(**values)


def patch_repo(monkeypatch):
    repo = MagicMock()
    monkeypatch.setattr(role_service, "RoleRepository", lambda _: repo)
    return repo


def test_create_role_success(db, monkeypatch):
    repo = patch_repo(monkeypatch)
    repo.get_by_code.return_value = None
    repo.get_by_code_including_deleted.return_value = None
    repo.get_by_name.return_value = None
    created = role(code="NEW_ROLE", name="New Role")
    repo.add.return_value = created

    result = role_service.create_role(10, " new_role ", " New Role ", "desc", db, user())

    assert result is created
    obj = repo.add.call_args.args[0]
    assert obj.code == "NEW_ROLE"
    assert obj.name == "New Role"
    assert obj.created_by == "admin@test.com"


def test_create_role_duplicate_code(db, monkeypatch):
    repo = patch_repo(monkeypatch)
    repo.get_by_code.return_value = role()

    with pytest.raises(HTTPException) as exc:
        role_service.create_role(10, "admin", "Admin", None, db)
    assert exc.value.status_code == 400


def test_create_role_reactivates_deleted(db, monkeypatch):
    repo = patch_repo(monkeypatch)
    deleted = role(status=3)
    repo.get_by_code.return_value = None
    repo.get_by_code_including_deleted.return_value = deleted
    repo.get_by_name.return_value = None
    repo.update.return_value = deleted

    result = role_service.create_role(10, "admin", "Reactivated", "d", db, user())

    assert result is deleted
    assert deleted.status == 1
    assert deleted.name == "Reactivated"
    assert deleted.updated_by == "admin@test.com"


def test_create_role_deleted_name_conflict(db, monkeypatch):
    repo = patch_repo(monkeypatch)
    deleted = role(status=3)
    repo.get_by_code.return_value = None
    repo.get_by_code_including_deleted.return_value = deleted
    repo.get_by_name.return_value = role(id=2)

    with pytest.raises(HTTPException) as exc:
        role_service.create_role(10, "admin", "Other", None, db)
    assert exc.value.status_code == 400


def test_create_role_reactivation_integrity_error(db, monkeypatch):
    repo = patch_repo(monkeypatch)
    deleted = role(status=3)
    repo.get_by_code.return_value = None
    repo.get_by_code_including_deleted.return_value = deleted
    repo.get_by_name.return_value = None
    repo.update.side_effect = IntegrityError("update", {}, Exception())

    with pytest.raises(HTTPException) as exc:
        role_service.create_role(10, "admin", "Admin", None, db)
    assert exc.value.status_code == 400
    db.rollback.assert_called_once_with()


def test_create_role_integrity_error(db, monkeypatch):
    repo = patch_repo(monkeypatch)
    repo.get_by_code.return_value = None
    repo.get_by_code_including_deleted.return_value = None
    repo.get_by_name.return_value = None
    repo.add.side_effect = IntegrityError("insert", {}, Exception())

    with pytest.raises(HTTPException) as exc:
        role_service.create_role(10, "new", "New", None, db)
    assert exc.value.status_code == 400
    db.rollback.assert_called_once_with()


def test_create_role_unexpected_error(db, monkeypatch):
    repo = patch_repo(monkeypatch)
    repo.get_by_code.return_value = None
    repo.get_by_code_including_deleted.return_value = None
    repo.get_by_name.return_value = None
    repo.add.side_effect = RuntimeError("db down")

    with pytest.raises(HTTPException) as exc:
        role_service.create_role(10, "new", "New", None, db)
    assert exc.value.status_code == 500


def test_create_role_duplicate_name(db, monkeypatch):
    repo = patch_repo(monkeypatch)
    repo.get_by_code.return_value = None
    repo.get_by_code_including_deleted.return_value = None
    repo.get_by_name.return_value = role()

    with pytest.raises(HTTPException) as exc:
        role_service.create_role(10, "new", "Admin", None, db)
    assert exc.value.status_code == 400


def test_list_roles(db, monkeypatch):
    repo = patch_repo(monkeypatch)
    roles = [role()]
    repo.get_all_by_tenant.return_value = roles
    assert role_service.list_roles(10, db, 1) == roles
    repo.get_all_by_tenant.assert_called_once_with(tenant_id=10, status_filter=1)


def test_get_role_success_and_not_found(db, monkeypatch):
    repo = patch_repo(monkeypatch)
    found = role()
    repo.get_by_id.return_value = found
    assert role_service.get_role(1, 10, db) is found

    repo.get_by_id.return_value = None
    with pytest.raises(HTTPException) as exc:
        role_service.get_role(1, 10, db)
    assert exc.value.status_code == 404


def test_update_role_success(db, monkeypatch):
    repo = patch_repo(monkeypatch)
    current = role()
    repo.get_by_id.return_value = current
    repo.get_by_code.return_value = None
    repo.get_by_name.return_value = None
    repo.update.return_value = current

    result = role_service.update_role(1, 10, "editor", "Editor", "desc", 0, db, user())

    assert result is current
    assert current.code == "editor"
    assert current.name == "Editor"
    assert current.status == 0
    assert current.description == "desc"
    assert current.updated_by == "admin@test.com"


def test_update_role_validation_errors(db, monkeypatch):
    repo = patch_repo(monkeypatch)
    current = role()
    repo.get_by_id.return_value = current

    repo.get_by_code.return_value = role(id=2)
    with pytest.raises(HTTPException) as exc:
        role_service.update_role(1, 10, "other", None, None, None, db)
    assert exc.value.status_code == 400

    repo.get_by_code.return_value = None
    with pytest.raises(HTTPException) as exc:
        role_service.update_role(1, 10, None, None, None, 9, db)
    assert exc.value.status_code == 400

    repo.get_by_name.return_value = role(id=2)
    with pytest.raises(HTTPException) as exc:
        role_service.update_role(1, 10, None, "Other", None, None, db)
    assert exc.value.status_code == 400


def test_update_role_not_found_and_integrity(db, monkeypatch):
    repo = patch_repo(monkeypatch)
    repo.get_by_id.return_value = None
    with pytest.raises(HTTPException) as exc:
        role_service.update_role(1, 10, None, None, None, None, db)
    assert exc.value.status_code == 404

    current = role()
    repo.get_by_id.return_value = current
    repo.update.side_effect = IntegrityError("update", {}, Exception())
    with pytest.raises(HTTPException) as exc:
        role_service.update_role(1, 10, None, None, None, None, db)
    assert exc.value.status_code == 400
    db.rollback.assert_called_once_with()


def test_delete_role_success_and_not_found(db, monkeypatch):
    repo = patch_repo(monkeypatch)
    current = role()
    repo.get_by_id.return_value = current
    result = role_service.delete_role(1, 10, db)
    assert result["id"] == 1
    assert result["message"] == "Rol eliminado correctamente"
    repo.delete.assert_called_once_with(current)

    repo.get_by_id.return_value = None
    with pytest.raises(HTTPException) as exc:
        role_service.delete_role(1, 10, db)
    assert exc.value.status_code == 404
