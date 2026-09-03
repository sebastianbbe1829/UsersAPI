from types import SimpleNamespace
from unittest.mock import MagicMock

from UsersAPI.repositories.tenant_repository import TenantRepository


def make_db(query_result=None):
    db = MagicMock()
    query = MagicMock()
    query.filter.return_value = query
    query.join.return_value = query
    query.all.return_value = query_result if query_result is not None else []
    query.first.return_value = query_result
    query.update.return_value = 1
    db.query.return_value = query
    db._query = query
    return db


def test_add_flushes_refreshes_and_returns_tenant():
    db = make_db()
    tenant = SimpleNamespace(id=1)
    result = TenantRepository(db).add(tenant)
    assert result is tenant
    db.add.assert_called_once_with(tenant)
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(tenant)


def test_get_all_without_status_filter():
    tenants = [SimpleNamespace(id=1)]
    db = make_db(tenants)
    assert TenantRepository(db).get_all() == tenants
    assert db._query.filter.call_count == 1


def test_get_all_with_status_filter():
    tenants = [SimpleNamespace(id=1, status=1)]
    db = make_db(tenants)
    assert TenantRepository(db).get_all(1) == tenants
    assert db._query.filter.call_count == 2


def test_get_by_id_returns_tenant():
    tenant = SimpleNamespace(id=7)
    db = make_db(tenant)
    assert TenantRepository(db).get_by_id(7) is tenant


def test_get_by_id_including_deleted_returns_tenant():
    tenant = SimpleNamespace(id=7)
    db = make_db(tenant)
    assert TenantRepository(db).get_by_id_including_deleted(7) is tenant


def test_get_by_slug_and_name_return_tenant():
    tenant = SimpleNamespace(id=7)
    db = make_db(tenant)
    repo = TenantRepository(db)
    assert repo.get_by_slug("tenant") is tenant
    assert repo.get_by_name("Tenant") is tenant


def test_update_flushes_twice_refreshes_and_returns_tenant():
    db = make_db()
    tenant = SimpleNamespace(id=1)
    assert TenantRepository(db).update(tenant) is tenant
    assert db.flush.call_count == 2
    db.refresh.assert_called_once_with(tenant)


def test_delete_marks_tenant_deleted_and_returns_tenant():
    db = make_db()
    tenant = SimpleNamespace(id=1)
    result = TenantRepository(db).delete(tenant)
    assert result is tenant
    db._query.update.assert_called_once()
    assert db.flush.call_count == 2
    db.refresh.assert_called_once_with(tenant)


def test_get_by_user_id_uses_default_active_status():
    tenants = [SimpleNamespace(id=1)]
    db = make_db(tenants)
    assert TenantRepository(db).get_by_user_id(20) == tenants
    assert db._query.join.call_count == 1
    assert db._query.filter.call_count == 1


def test_get_by_user_id_with_status_filter_adds_filter():
    tenants = [SimpleNamespace(id=1)]
    db = make_db(tenants)
    assert TenantRepository(db).get_by_user_id(20, 2) == tenants
    assert db._query.join.call_count == 1
    assert db._query.filter.call_count == 2


def test_get_by_user_id_without_status_filter_does_not_add_extra_filter():
    db = make_db([])
    assert TenantRepository(db).get_by_user_id(20, None) == []
    assert db._query.filter.call_count == 1
