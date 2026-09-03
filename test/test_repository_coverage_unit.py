from types import SimpleNamespace
from unittest.mock import MagicMock

from UsersAPI.repositories.permission_repository import PermissionRepository
from UsersAPI.repositories.role_permission_repository import RolePermissionRepository
from UsersAPI.repositories.role_repository import RoleRepository
from UsersAPI.repositories.user_repository import UserRepository
from UsersAPI.repositories.user_tenant_repository import UserTenantRepository
from UsersAPI.repositories.user_tenant_role_repository import UserTenantRoleRepository


def _db():
    query = MagicMock()
    query.filter.return_value = query
    query.join.return_value = query
    query.update.return_value = None
    db = MagicMock()
    db.query.return_value = query
    return db, query


def test_permission_repository_queries_and_create():
    db, query = _db()
    active = SimpleNamespace(id=1)
    query.first.return_value = active
    query.all.return_value = [active]
    repo = PermissionRepository(db)
    assert repo.get_by_code("USER_READ") is active
    assert repo.get_by_code_any_status("USER_READ") is active
    assert repo.get_all_by_permission() == [active]
    permission = SimpleNamespace(id=2)
    assert repo.create(permission) is permission
    db.add.assert_called_once_with(permission)
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(permission)


def test_role_permission_repository_queries_and_add_delete():
    db, query = _db()
    relation = SimpleNamespace(id=7)
    query.first.return_value = relation
    query.all.return_value = [relation]
    repo = RolePermissionRepository(db)
    assert repo.get_by_role_permission(3, 4) is relation
    assert repo.get_permissions_by_role(3) == [relation]
    assert repo.get_by_id(7) is relation
    new_relation = SimpleNamespace(id=8)
    assert repo.add(new_relation) is new_relation
    repo.delete(relation)
    db.add.assert_called_once_with(new_relation)
    db.delete.assert_called_once_with(relation)
    assert db.flush.call_count == 2
    db.refresh.assert_called_once_with(new_relation)


def test_user_repository_queries_and_mutations():
    db, query = _db()
    user = SimpleNamespace(id=11, dni="123")
    query.first.return_value = user
    query.all.return_value = [user]
    repo = UserRepository(db)
    assert repo.add(user) is user
    assert repo.get_all() == [user]
    assert repo.get_by_dni("123") is user
    assert repo.get_by_id(11) is user
    assert repo.get_by_dni_in_tenant("123", 2) is user
    assert repo.get_by_id_and_tenant(11, 2) is user
    assert repo.get_all_by_tenant(2) == [user]
    assert repo.get_all_by_tenant(2, status_filter=1) == [user]
    assert repo.get_by_id_including_deleted(11) is user
    assert repo.update(user) is user
    assert db.add.call_count == 2
    assert db.flush.call_count == 2


def test_role_repository_covers_all_queries_and_mutations():
    db, query = _db()
    role = SimpleNamespace(id=10, code="ADMIN", name="Administrador")
    query.first.return_value = role
    query.all.return_value = [role]
    repo = RoleRepository(db)
    assert repo.get_all_by_tenant(7) == [role]
    assert repo.get_all_by_tenant(7, status_filter=1) == [role]
    assert repo.get_by_id(10, 7) is role
    assert repo.get_by_code("ADMIN", 7) is role
    assert repo.get_by_code_including_deleted("ADMIN", 7) is role
    assert repo.get_by_name("Administrador", 7) is role
    assert repo.get_by_name_including_deleted("Administrador", 7) is role
    new_role = SimpleNamespace(id=11)
    assert repo.add(new_role) is new_role
    assert repo.update(role) is role
    assert repo.delete(role) is role
    assert db.add.assert_called_once_with(new_role) is None
    query.update.assert_called_once()
    assert db.flush.call_count == 5
    assert db.refresh.call_count == 3


def test_user_tenant_repository_covers_all_queries_and_mutations():
    db, query = _db()
    association = SimpleNamespace(id=20, status=1)
    query.first.return_value = association
    query.all.return_value = [association]
    repo = UserTenantRepository(db)
    assert repo.add(association) is association
    assert repo.add_without_commit(association) is association
    assert repo.get_by_id(20) is association
    assert repo.get_by_id_including_deleted(20) is association
    assert repo.get_by_user_and_tenant(5, 7) is association
    assert repo.get_by_user_and_tenant_including_deleted(5, 7) is association
    assert repo.get_by_activation_token("token") is association
    assert repo.get_by_user(5) == [association]
    assert repo.get_by_tenant(7) == [association]
    assert repo.update(association) is association
    assert repo.mark_dirty(association) is association
    assert repo.delete(association) is association
    assert association.status == 3
    assert db.add.call_count == 5
    assert db.flush.call_count == 5


def test_user_tenant_role_repository_covers_all_methods():
    db, query = _db()
    relation = SimpleNamespace(id=30)
    query.first.return_value = relation
    query.all.return_value = [relation]
    repo = UserTenantRoleRepository(db)
    new_relation = SimpleNamespace(id=31)
    assert repo.add(new_relation) is new_relation
    assert repo.get_by_id(30) is relation
    assert repo.get_by_user_tenant_and_role(20, 10) is relation
    assert repo.get_all_by_user_tenant(20) == [relation]
    assert repo.delete(relation) is relation
    db.add.assert_called_once_with(new_relation)
    db.refresh.assert_called_once_with(new_relation)
    db.delete.assert_called_once_with(relation)
    assert db.flush.call_count == 2
