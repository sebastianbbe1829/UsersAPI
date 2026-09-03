from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from UsersAPI.services import user_tenant_role_service as service


def _query_chain(*results):
    query = MagicMock()
    query.filter.return_value = query
    query.first.side_effect = list(results)
    return query


def test_assign_role_success(monkeypatch):
    db = MagicMock()
    db.query.side_effect = [
        _query_chain(SimpleNamespace(user_id=10)),
        _query_chain(SimpleNamespace(id=10)),
        _query_chain(SimpleNamespace(id=20)),
    ]
    repo = MagicMock()
    created = SimpleNamespace(id=30)
    repo.add.return_value = created
    repo.get_by_user_tenant_and_role.return_value = None
    monkeypatch.setattr(service, "UserTenantRoleRepository", lambda _: repo)

    result = service.assign_role_to_user(1, 20, 5, db)

    assert result is created
    repo.add.assert_called_once()


@pytest.mark.parametrize(
    "query_results,detail",
    [
        ([None], "La relación usuario-tenant no existe"),
        ([SimpleNamespace(user_id=10), None], "El usuario no existe"),
        (
            [SimpleNamespace(user_id=10), SimpleNamespace(id=10), None],
            "El rol no existe en el tenant seleccionado",
        ),
    ],
)
def test_assign_role_validates_context(query_results, detail):
    db = MagicMock()
    queries = [_query_chain(result) for result in query_results]
    db.query.side_effect = queries
    monkeypatch = pytest.MonkeyPatch()
    repo = MagicMock()
    monkeypatch.setattr(service, "UserTenantRoleRepository", lambda _: repo)
    try:
        with pytest.raises(HTTPException) as exc:
            service.assign_role_to_user(1, 20, 5, db)
        assert exc.value.status_code == 404
        assert exc.value.detail == detail
    finally:
        monkeypatch.undo()


def test_assign_role_rejects_existing(monkeypatch):
    db = MagicMock()
    db.query.side_effect = [
        _query_chain(SimpleNamespace(user_id=10)),
        _query_chain(SimpleNamespace(id=10)),
        _query_chain(SimpleNamespace(id=20)),
    ]
    repo = MagicMock()
    repo.get_by_user_tenant_and_role.return_value = SimpleNamespace(id=99)
    monkeypatch.setattr(service, "UserTenantRoleRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        service.assign_role_to_user(1, 20, 5, db)
    assert exc.value.status_code == 400


def test_assign_role_integrity_error(monkeypatch):
    db = MagicMock()
    db.query.side_effect = [
        _query_chain(SimpleNamespace(user_id=10)),
        _query_chain(SimpleNamespace(id=10)),
        _query_chain(SimpleNamespace(id=20)),
    ]
    repo = MagicMock()
    repo.get_by_user_tenant_and_role.return_value = None
    repo.add.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
    monkeypatch.setattr(service, "UserTenantRoleRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        service.assign_role_to_user(1, 20, 5, db)
    assert exc.value.status_code == 400
    db.rollback.assert_called_once()


def test_assign_role_unexpected_error(monkeypatch):
    db = MagicMock()
    db.query.side_effect = [
        _query_chain(SimpleNamespace(user_id=10)),
        _query_chain(SimpleNamespace(id=10)),
        _query_chain(SimpleNamespace(id=20)),
    ]
    repo = MagicMock()
    repo.get_by_user_tenant_and_role.return_value = None
    repo.add.side_effect = RuntimeError("boom")
    monkeypatch.setattr(service, "UserTenantRoleRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        service.assign_role_to_user(1, 20, 5, db)
    assert exc.value.status_code == 500
    db.rollback.assert_called_once()


def test_list_user_roles_success():
    db = MagicMock()
    db.query.side_effect = [
        _query_chain(SimpleNamespace(user_id=10)),
        _query_chain(SimpleNamespace(id=10)),
    ]
    repo = MagicMock()
    roles = [SimpleNamespace(role_id=20)]
    repo.get_all_by_user_tenant.return_value = roles
    service_repo = service.UserTenantRoleRepository
    service.UserTenantRoleRepository = lambda _: repo
    try:
        assert service.list_user_roles(1, 5, db) == roles
    finally:
        service.UserTenantRoleRepository = service_repo


def test_list_user_roles_missing_relation():
    db = MagicMock()
    db.query.side_effect = [_query_chain(None)]
    with pytest.raises(HTTPException) as exc:
        service.list_user_roles(1, 5, db)
    assert exc.value.status_code == 404


def test_list_user_roles_missing_user():
    db = MagicMock()
    db.query.side_effect = [
        _query_chain(SimpleNamespace(user_id=10)),
        _query_chain(None),
    ]
    with pytest.raises(HTTPException) as exc:
        service.list_user_roles(1, 5, db)
    assert exc.value.status_code == 404


def test_delete_user_role_success(monkeypatch):
    db = MagicMock()
    assignment = SimpleNamespace(id=30, user_tenant_id=1, role_id=20)
    db.query.side_effect = [
        _query_chain(SimpleNamespace(user_id=10)),
        _query_chain(SimpleNamespace(id=10)),
        _query_chain(SimpleNamespace(id=20)),
    ]
    repo = MagicMock()
    repo.get_by_id.return_value = assignment
    monkeypatch.setattr(service, "UserTenantRoleRepository", lambda _: repo)

    result = service.delete_user_role(30, 5, db)

    assert result["id"] == 30
    assert result["role_id"] == 20
    repo.delete.assert_called_once_with(assignment)


def test_delete_user_role_missing_assignment(monkeypatch):
    db = MagicMock()
    repo = MagicMock()
    repo.get_by_id.return_value = None
    monkeypatch.setattr(service, "UserTenantRoleRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        service.delete_user_role(30, 5, db)
    assert exc.value.status_code == 404


def test_delete_user_role_wrong_tenant(monkeypatch):
    db = MagicMock()
    assignment = SimpleNamespace(id=30, user_tenant_id=1, role_id=20)
    db.query.side_effect = [_query_chain(None)]
    repo = MagicMock()
    repo.get_by_id.return_value = assignment
    monkeypatch.setattr(service, "UserTenantRoleRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        service.delete_user_role(30, 5, db)
    assert exc.value.status_code == 404


def test_delete_user_role_missing_user(monkeypatch):
    db = MagicMock()
    assignment = SimpleNamespace(id=30, user_tenant_id=1, role_id=20)
    db.query.side_effect = [
        _query_chain(SimpleNamespace(user_id=10)),
        _query_chain(None),
    ]
    repo = MagicMock()
    repo.get_by_id.return_value = assignment
    monkeypatch.setattr(service, "UserTenantRoleRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        service.delete_user_role(30, 5, db)
    assert exc.value.status_code == 404


def test_delete_user_role_missing_role(monkeypatch):
    db = MagicMock()
    assignment = SimpleNamespace(id=30, user_tenant_id=1, role_id=20)
    db.query.side_effect = [
        _query_chain(SimpleNamespace(user_id=10)),
        _query_chain(SimpleNamespace(id=10)),
        _query_chain(None),
    ]
    repo = MagicMock()
    repo.get_by_id.return_value = assignment
    monkeypatch.setattr(service, "UserTenantRoleRepository", lambda _: repo)

    with pytest.raises(HTTPException) as exc:
        service.delete_user_role(30, 5, db)
    assert exc.value.status_code == 404
