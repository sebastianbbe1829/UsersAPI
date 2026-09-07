from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from UsersAPI.domains.clients.services.compliance_override_service import override_client_compliance
from UsersAPI.domains.clients.schemas.compliance_override import ClientComplianceOverrideRequest
from UsersAPI.domains.core.models import GlobalUserDB


def _payload(otp="123456"):
    return ClientComplianceOverrideRequest(
        reason="Autorización formal de cumplimiento para liberar la restricción.",
        otp=otp,
    )


def _super_user():
    return GlobalUserDB(
        id=7,
        email="super@example.com",
        is_superuser=True,
        is_active=True,
        mfa_enabled=True,
        mfa_secret_encrypted="encrypted-secret",
    )


def test_override_requires_valid_mfa():
    db = MagicMock()
    user = _super_user()

    with patch(
        "UsersAPI.domains.clients.services.compliance_override_service._decrypt_mfa_secret",
        return_value="JBSWY3DPEHPK3PXP",
    ):
        with pytest.raises(HTTPException) as exc:
            override_client_compliance(uuid4(), _payload("000000"), db, 10, user)

    assert exc.value.status_code == 401


def test_override_requires_super_user():
    db = MagicMock()
    user = SimpleNamespace(is_superuser=False)

    with pytest.raises(HTTPException) as exc:
        override_client_compliance(uuid4(), _payload(), db, 10, user)

    assert exc.value.status_code == 403


def test_override_releases_blocked_client_and_records_audit():
    db = MagicMock()
    client = SimpleNamespace(
        id=uuid4(), tenant_id=10, status="BLOCKED", is_listed=True,
        screenings=[SimpleNamespace(id=uuid4(), requested_at=None)],
        updated_at=None, updated_by=None,
    )
    db.query.return_value.filter.return_value.first.return_value = client
    user = _super_user()

    with patch(
        "UsersAPI.domains.clients.services.compliance_override_service._decrypt_mfa_secret",
        return_value="JBSWY3DPEHPK3PXP",
    ), patch(
        "UsersAPI.domains.clients.services.compliance_override_service.pyotp.TOTP.verify",
        return_value=True,
    ):
        result = override_client_compliance(uuid4(), _payload(), db, 10, user)

    assert result.client_id == client.id
    assert result.screening_id == client.screenings[0].id
    assert result.requested_by == user.id
    assert client.status == "ACTIVE"
    assert client.is_listed is True
    db.add.assert_called()
    db.flush.assert_called()
