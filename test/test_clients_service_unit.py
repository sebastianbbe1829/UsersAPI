from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from uuid import uuid4

from UsersAPI.domains.clients.models import IdentificationTypeDB
from UsersAPI.domains.clients.repositories.client_repository import ClientRepository
from UsersAPI.domains.clients.schemas.client import ClientUpdate
from UsersAPI.domains.clients.services import client_service


def test_create_client_sets_audit_and_consent_fields():
    db = MagicMock()
    data = MagicMock()
    data.person_type = "NATURAL"
    data.identification_type_id = 1
    data.identification_number = "123456789"
    data.first_name = "Sebastian"
    data.middle_name = None
    data.last_name = "Buitrago"
    data.second_last_name = None
    data.business_name = None
    data.consent_given = True
    data.consent_at = None
    data.model_dump.return_value = {
        "identification_type_id": 1,
        "identification_number": "123456789",
        "person_type": "NATURAL",
        "first_name": "Sebastian",
        "middle_name": None,
        "last_name": "Buitrago",
        "second_last_name": None,
        "business_name": None,
        "consent_given": True,
    }
    repository = MagicMock()
    repository.get_by_identification.return_value = None
    repository.add.side_effect = lambda client: client

    with patch.object(
        client_service, "ClientRepository", return_value=repository
    ), patch.object(client_service, "_validate_identity_data"):
        result = client_service.create_client(
            data, db, 10, SimpleNamespace(email="user@example.com")
        )

    assert result.created_by == "user@example.com"
    assert result.consent_at is not None
    assert result.consent_at.tzinfo is not None


def test_create_client_uses_system_as_audit_actor_when_user_has_no_identity():
    db = MagicMock()
    data = MagicMock()
    data.person_type = "NATURAL"
    data.identification_type_id = 1
    data.identification_number = "123456789"
    data.first_name = "Sebastian"
    data.middle_name = None
    data.last_name = "Buitrago"
    data.second_last_name = None
    data.business_name = None
    data.consent_given = False
    data.consent_at = None
    data.model_dump.return_value = {
        "identification_type_id": 1,
        "identification_number": "123456789",
        "person_type": "NATURAL",
        "first_name": "Sebastian",
        "middle_name": None,
        "last_name": "Buitrago",
        "second_last_name": None,
        "business_name": None,
        "consent_given": False,
    }
    repository = MagicMock()
    repository.get_by_identification.return_value = None
    repository.add.side_effect = lambda client: client

    with patch.object(
        client_service, "ClientRepository", return_value=repository
    ), patch.object(client_service, "_validate_identity_data"):
        result = client_service.create_client(data, db, 10, SimpleNamespace())

    assert result.created_by == "system"


def test_update_client_regenerates_full_name_and_audit_fields():
    db = MagicMock()
    client_id = uuid4()
    target = SimpleNamespace(
        id=client_id,
        tenant_id=10,
        identification_type_id=1,
        identification_number="123456789",
        person_type="NATURAL",
        first_name="Sebastian",
        middle_name=None,
        last_name="Buitrago",
        second_last_name=None,
        business_name=None,
        email="old@example.com",
        address="CRA 1 # 2-3",
        consent_given=True,
        consent_at=None,
        consent_source="FORMULARIO",
        status="ACTIVE",
        compliance_status="CLEAR",
        is_listed=False,
        credit_limit=0,
    )
    data = MagicMock()
    data.model_dump.return_value = {"first_name": "Juan", "last_name": "Pérez"}

    with patch.object(
        client_service, "get_client", return_value=target
    ), patch.object(
        client_service, "_validate_identity_data"
    ), patch.object(
        client_service.ClientRepository,
        "update",
        side_effect=lambda client: client,
    ):
        result = client_service.update_client(
            client_id,
            data,
            db,
            10,
            SimpleNamespace(email="editor@example.com"),
        )

    assert result.full_name == "JUAN PÉREZ"
    assert result.updated_by == "editor@example.com"
    assert result.updated_at.tzinfo is not None


def test_update_client_clears_consent_timestamp_when_consent_revoked():
    db = MagicMock()
    client_id = uuid4()
    target = SimpleNamespace(
        id=client_id,
        tenant_id=10,
        identification_type_id=1,
        identification_number="123456789",
        person_type="NATURAL",
        first_name="Sebastian",
        middle_name=None,
        last_name="Buitrago",
        second_last_name=None,
        business_name=None,
        email="old@example.com",
        address="CRA 1 # 2-3",
        consent_given=True,
        consent_at=datetime.now(UTC),
        consent_source="FORMULARIO",
        status="ACTIVE",
        compliance_status="CLEAR",
        is_listed=False,
        credit_limit=0,
    )
    data = ClientUpdate(consent_given=False)

    with patch.object(
        client_service, "get_client", return_value=target
    ), patch.object(
        client_service, "_validate_identity_data"
    ), patch.object(
        client_service.ClientRepository,
        "update",
        side_effect=lambda client: client,
    ):
        result = client_service.update_client(
            client_id,
            data,
            db,
            10,
            SimpleNamespace(email="editor@example.com"),
        )

    assert result.consent_given is False
    assert result.consent_at is None


def test_validate_identification_type_rejects_missing_type():
    db = MagicMock()
    query = MagicMock()
    query.filter.return_value = query
    query.first.return_value = None
    db.query.return_value = query

    with pytest.raises(HTTPException) as exc:
        client_service._validate_identification_type(db, 99, "NATURAL")

    assert exc.value.status_code == 400
    assert "not found" in exc.value.detail


def test_validate_identification_type_rejects_person_type_mismatch():
    db = MagicMock()
    query = MagicMock()
    query.filter.return_value = query
    query.first.return_value = IdentificationTypeDB(
        id=1,
        code="CC",
        name="Cédula",
        person_type="NATURAL",
        active=True,
    )
    db.query.return_value = query

    with pytest.raises(HTTPException) as exc:
        client_service._validate_identification_type(db, 1, "JURIDICA")

    assert exc.value.status_code == 400
    assert "person type" in exc.value.detail


def test_full_name_uses_business_name_for_legal_person():
    data = SimpleNamespace(person_type="JURIDICA", business_name="  ACME   S.A. ")
    assert client_service._full_name(data) == "ACME S.A."


def test_create_client_rejects_blocked_status_before_persistence():
    data = SimpleNamespace(status="BLOCKED")

    with pytest.raises(HTTPException) as exc:
        client_service.create_client(data, MagicMock(), 10, SimpleNamespace())

    assert exc.value.status_code == 400


def test_create_client_rejects_duplicate_identification():
    db = MagicMock()
    data = MagicMock()
    data.status = "ACTIVE"
    data.person_type = "NATURAL"
    data.identification_type_id = 1
    data.identification_number = "123"
    data.first_name = "Juan"
    data.middle_name = None
    data.last_name = "Perez"
    data.second_last_name = None
    data.business_name = None
    data.consent_given = False
    data.consent_at = None
    repository = MagicMock()
    repository.get_by_identification.return_value = object()

    with patch.object(
        client_service, "ClientRepository", return_value=repository
    ), patch.object(client_service, "_validate_identity_data"):
        with pytest.raises(HTTPException) as exc:
            client_service.create_client(
                data, db, 10, SimpleNamespace(email="user@example.com")
            )

    assert exc.value.status_code == 409


def test_get_client_raises_when_not_found():
    client_id = uuid4()
    repository = MagicMock()
    repository.get_by_id.return_value = None

    with patch.object(client_service, "ClientRepository", return_value=repository):
        with pytest.raises(HTTPException) as exc:
            client_service.get_client(client_id, MagicMock(), 10)

    assert exc.value.status_code == 404


def test_list_and_delete_clients_delegate_to_repository():
    db = MagicMock()
    repository = MagicMock()
    client = SimpleNamespace(id=uuid4(), credit_limit=0)
    repository.get_all.return_value = [client]

    with patch.object(client_service, "ClientRepository", return_value=repository):
        with patch.object(client_service, "_credit_used_map", return_value={}):
            assert client_service.list_clients(db, 10, limit=20, offset=5, search="juan") == [
                client
            ]
        with patch.object(client_service, "get_client", return_value=client):
            client_service.delete_client(client.id, db, 10)

    repository.get_all.assert_called_once_with(
        10,
        limit=20,
        offset=5,
        search="juan",
    )
    repository.update.assert_called_once_with(client)


def test_client_repository_get_all_applies_search_and_pagination():
    db = MagicMock()
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.offset.return_value = query
    query.limit.return_value = query
    query.all.return_value = ["client"]
    db.query.return_value = query

    result = ClientRepository(db).get_all(10, limit=20, offset=-3, search="  juan ")

    assert result == ["client"]
    assert query.filter.call_count == 2
    query.offset.assert_called_once_with(0)
    query.limit.assert_called_once_with(20)


def test_client_repository_crud_methods_delegate_to_session():
    db = MagicMock()
    client = SimpleNamespace(id=uuid4())
    repository = ClientRepository(db)

    assert repository.add(client) is client
    assert repository.update(client) is client
    repository.delete(client)
    repository.get_by_id(client.id, 10)
    repository.get_by_identification(1, "123", 10)

    assert db.add.call_count == 3
    assert db.flush.call_count == 3
    db.delete.assert_not_called()
