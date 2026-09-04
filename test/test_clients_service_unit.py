from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from uuid import uuid4

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

    assert result.full_name == "Juan Pérez"
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
