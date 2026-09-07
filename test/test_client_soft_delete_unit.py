from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from UsersAPI.domains.clients.services import client_service


def test_delete_client_logically_deactivates_and_audits_actor(monkeypatch):
    client_id = uuid4()
    client = SimpleNamespace(
        id=client_id,
        status="ACTIVE",
        updated_at=None,
        updated_by=None,
    )
    current_user = SimpleNamespace(email="admin@example.com")
    repository = MagicMock()
    repository.update.return_value = client

    monkeypatch.setattr(
        client_service,
        "get_client",
        MagicMock(return_value=client),
    )
    monkeypatch.setattr(
        client_service,
        "ClientRepository",
        MagicMock(return_value=repository),
    )

    result = client_service.delete_client(
        client_id,
        MagicMock(),
        10,
        current_user,
    )

    assert result is None
    assert client.status == "INACTIVE"
    assert client.updated_at is not None
    assert client.updated_by == "admin@example.com"
    repository.update.assert_called_once_with(client)


def test_delete_client_uses_username_when_email_is_missing(monkeypatch):
    client = SimpleNamespace(
        status="ACTIVE",
        updated_at=None,
        updated_by=None,
    )
    current_user = SimpleNamespace(username="operator")
    repository = MagicMock()

    monkeypatch.setattr(
        client_service,
        "get_client",
        MagicMock(return_value=client),
    )
    monkeypatch.setattr(
        client_service,
        "ClientRepository",
        MagicMock(return_value=repository),
    )

    client_service.delete_client(uuid4(), MagicMock(), 10, current_user)

    assert client.status == "INACTIVE"
    assert client.updated_by == "operator"


def test_delete_client_propagates_not_found(monkeypatch):
    not_found = HTTPException(status_code=404, detail="Client not found")
    monkeypatch.setattr(
        client_service,
        "get_client",
        MagicMock(side_effect=not_found),
    )

    with pytest.raises(HTTPException) as exc:
        client_service.delete_client(
            uuid4(),
            MagicMock(),
            10,
            SimpleNamespace(email="admin@example.com"),
        )

    assert exc.value.status_code == 404
