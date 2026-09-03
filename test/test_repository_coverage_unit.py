from types import SimpleNamespace
from unittest.mock import MagicMock

from UsersAPI.repositories.permission_repository import PermissionRepository
from UsersAPI.repositories.role_permission_repository import RolePermissionRepository


def _db():
    query = MagicMock()
    query.filter.return_value = query
    db = MagicMock()
    db.query.return_value = query
    return db, query


def test_permission_repository_queries_and_create():
    db, query = _db()
    active = SimpleNamespace(id=1)
    all_permissions = [active]
    query.first.return_value = active
    query.all.return_value = all_permissions
    repo = PermissionRepository(db)

    assert repo.get_by_code("USER_READ") is active
    assert repo.get_by_code_any_status("USER_READ") is active
    assert repo.get_all_by_permission() == all_permissions

    permission = SimpleNamespace(id=2)
    assert repo.create(permission) is permission
    db.add.assert_called_once_with(permission)
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(permission)


def test_role_permission_repository_queries_and_add_delete():
    db, query = _db()
    relation = SimpleNamespace(id=7)
    permissions = [relation]
    query.first.return_value = relation
    query.all.return_value = permissions
    repo = RolePermissionRepository(db)

    assert repo.get_by_role_permission(3, 4) is relation
    assert repo.get_permissions_by_role(3) == permissions
    assert repo.get_by_id(7) is relation

    new_relation = SimpleNamespace(id=8)
    assert repo.add(new_relation) is new_relation
    db.add.assert_called_once_with(new_relation)
    assert db.flush.call_count == 1
    db.refresh.assert_called_once_with(new_relation)

    repo.delete(relation)
    db.delete.assert_called_once_with(relation)
    assert db.flush.call_count == 2
