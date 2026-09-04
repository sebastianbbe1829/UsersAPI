from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from UsersAPI.domains.clients.models import ClientDB
from UsersAPI.domains.clients.schemas.client import ClientCreate, ClientUpdate
from UsersAPI.domains.clients.services import client_service


def _natural_data(**overrides):
    data = {
        "identification_type_id": 1,
        "identification_number": "123456789",
        "person_type": "NATURAL",
        "first_name": "Sebastian",
        "last_name": "Buitrago",
        "email": "sebastian@example.com",
    }
    data.update(overrides)
    return ClientCreate(**data)


def _legal_data(**overrides):
    data = {
        "identification_type_id": 4,
        "identification_number": "900123456",
        "person_type": "JURIDICA",
        "business_name": "Empresa Demo SAS",
    }
    data.update(overrides)
    return ClientCreate(**data)


def test_full_name_for_natural_person():
    data = _natural_data(
        first_name=" Sebastian ",
        middle_name="Andrés",
        last_name=" Buitrago ",
        second_last_name="Betancur",
    )

    assert client_service._full_name(data) == "Sebastian Andrés Buitrago Betancur"


def test_full_name_for_legal_person():
    assert client_service._full_name(_legal_data(business_name=" Empresa Demo SAS ")) == "Empresa Demo SAS"


def test_create_client_sets_audit_and_consent_fields():
    db = MagicMock()
    actor = SimpleNamespace(email="admin@example.com")
    data = _natural_data(consent_given=True, consent_source="WEB")

    with patch.object(client_service, "_validate_identity_data"), patch.object(
        client_service.ClientRepository, "get_by_identification", return_value=None
    ), patch.object(client_service.ClientRepository, "add", side_effect=lambda client: client):
        client = client_service.create_client(data, db, 10, actor)

    assert isinstance(client, ClientDB)
    assert client.tenant_id == 10
    assert client.full_name == "Sebastian Buitrago"
    assert client.created_by == "admin@example.com"
    assert client.consent_given is True
    assert client.consent_source == "WEB"
    assert client.consent_at is not None


def test_create_client_rejects_duplicate_identification():
    db = MagicMock()
    data = _natural_data()
    duplicate = SimpleNamespace(id=uuid4())

    with patch.object(client_service, "_validate_identity_data"), patch.object(
        client_service.ClientRepository, "get_by_identification", return_value=duplicate
    ):
        with pytest.raises(HTTPException) as exc_info:
            client_service.create_client(data, db, 10, SimpleNamespace(email="admin@example.com"))

    assert exc_info.value.status_code == 409


def test_create_client_uses_system_as_audit_actor_when_user_has_no_identity():
    db = MagicMock()
    data = _legal_data()

    with patch.object(client_service, "_validate_identity_data"), patch.object(
        client_service.ClientRepository, "get_by_identification", return_value=None
    ), patch.object(client_service.ClientRepository, "add", side_effect=lambda client: client):
        client = client_service.create_client(data, db, 20, object())

    assert client.created_by == "system"


def test_update_client_regenerates_full_name_and_audit_fields():
    db = MagicMock()
    client_id = uuid4()
    target = SimpleNamespace(
        id=client_id,
        tenant_id=10,
        identification_type_id=1,
        identification_number="123456789",
        person_type="NATURAL",
        first_name="Old",
        middle_name=None,
        last_name="Name",
        second_last_name=None,
        business_name=None,
        consent_given=False,
        consent_at=None,
    )
    data = ClientUpdate(first_name="New", last_name="Person")
    actor = SimpleNamespace(email="editor@example.com")

    with patch.object(client_service, "get_client", return_value=target), patch.object(
        client_service, "_validate_identity_data"
    ), patch.object(client_service.ClientRepository, "update", side_effect=lambda client: client):
        result = client_service.update_client(client_id, data, db, 10, actor)

    assert result.full_name == "New Person"
    assert result.updated_by == "editor@example.com"
    assert result.updated_at is not None


def test_update_client_rejects_invalid_person_identity():
    db = MagicMock()
    client_id = uuid4()
    target = SimpleNamespace(
        id=client_id,
        tenant_id=10,
        identification_type_id=1,
        identification_number="123456789",
        person_type="JURIDICA",
        first_name=None,
        middle_name=None,
        last_name=None,
        second_last_name=None,
        business_name=None,
        consent_given=False,
        consent_at=None,
    )
    data = ClientUpdate(person_type="JURIDICA")

    with patch.object(client_service, "get_client", return_value=target), patch.object(
        client_service,
        "_validate_identity_data",
        side_effect=HTTPException(status_code=400, detail="Legal person requires business_name"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            client_service.update_client(client_id, data, db, 10, SimpleNamespace(email="editor@example.com"))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Legal person requires business_name"


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
        consent_given=True,
        consent_at=client_service.datetime.utcnow(),
    )
    data = ClientUpdate(consent_given=False)

    with patch.object(client_service, "get_client", return_value=target), patch.object(
        client_service, "_validate_identity_data"
    ), patch.object(client_service.ClientRepository, "update", side_effect=lambda client: client):
        result = client_service.update_client(client_id, data, db, 10, SimpleNamespace(email="editor@example.com"))

    assert result.consent_given is False
    assert result.consent_at is None


def test_delete_client_is_tenant_scoped():
    db = MagicMock()
    client = SimpleNamespace(id=uuid4())

    with patch.object(client_service, "get_client", return_value=client), patch.object(
        client_service.ClientRepository, "delete"
    ) as delete_mock:
        client_service.delete_client(client.id, db, 55)

    delete_mock.assert_called_once_with(client)
