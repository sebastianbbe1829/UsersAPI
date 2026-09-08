from types import SimpleNamespace
from uuid import uuid4

from unittest.mock import MagicMock

from UsersAPI.domains.clients.schemas.compliance_override import ClientComplianceOverrideRequest
from UsersAPI.domains.clients.services.compliance_override_service import override_client_compliance
from UsersAPI.domains.core.models import UserTenantDB


def _payload():
    return ClientComplianceOverrideRequest(
        reason="Autorización formal de cumplimiento para liberar la restricción."
    )


def _tenant_user():
    return UserTenantDB(
        id=7,
        email="admin@example.com",
        tenant_id=10,
        status=1,
    )


def test_override_does_not_require_mfa():
    db = MagicMock()
    client = SimpleNamespace(
        id=uuid4(), tenant_id=10, status="BLOCKED", is_listed=True,
        screenings=[], updated_at=None, updated_by=None,
    )
    db.query.return_value.filter.return_value.first.return_value = client
    user = _tenant_user()

    result = override_client_compliance(uuid4(), _payload(), db, 10, user)

    assert result.client_id == client.id
    assert result.requested_by == user.id
    assert result.requested_by_email == user.email
    assert result.reason == _payload().reason
    assert client.status == "ACTIVE"
    assert client.is_listed is False
    db.add.assert_called()
    db.flush.assert_called()


def test_override_preserves_original_match_history():
    db = MagicMock()
    screening = SimpleNamespace(id=uuid4(), requested_at=None)
    client = SimpleNamespace(
        id=uuid4(), tenant_id=10, status="BLOCKED", is_listed=True,
        screenings=[screening], updated_at=None, updated_by=None,
    )
    db.query.return_value.filter.return_value.first.return_value = client
    user = _tenant_user()

    result = override_client_compliance(uuid4(), _payload(), db, 10, user)

    assert result.screening_id == screening.id
    assert client.is_listed is False
    assert client.status == "ACTIVE"
    assert client.screenings == [screening]


def test_override_rejects_client_without_active_compliance_restriction():
    from fastapi import HTTPException

    db = MagicMock()
    client = SimpleNamespace(
        id=uuid4(), tenant_id=10, status="ACTIVE", is_listed=False,
        screenings=[], updated_at=None, updated_by=None,
    )
    db.query.return_value.filter.return_value.first.return_value = client

    try:
        override_client_compliance(uuid4(), _payload(), db, 10, _tenant_user())
        raise AssertionError("Expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 409
