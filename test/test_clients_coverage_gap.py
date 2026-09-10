from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from UsersAPI.domains.clients.services import compliance_report_service
from UsersAPI.domains.clients.services import screening_provider


class _QueryMock:
    def __init__(self, all_result=None, first_result=None):
        self._all_result = all_result or []
        self._first_result = first_result

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def all(self):
        return self._all_result

    def first(self):
        return self._first_result


def test_restricted_report_marks_blocked_and_lifted_clients():
    now = datetime.now(UTC)
    blocked = SimpleNamespace(
        id=uuid4(),
        tenant_id=10,
        identification_number="111",
        full_name="BLOCKED",
        person_type="NATURAL",
        status="BLOCKED",
        compliance_status="MATCH",
        list_type="OFAC",
        is_listed=True,
        created_at=now,
        created_by="admin",
    )
    lifted = SimpleNamespace(
        id=uuid4(),
        tenant_id=10,
        identification_number="222",
        full_name="LIFTED",
        person_type="NATURAL",
        status="ACTIVE",
        compliance_status="MATCH",
        list_type="OFAC",
        is_listed=True,
        created_at=now,
        created_by="admin",
    )
    screening_blocked = SimpleNamespace(
        id=uuid4(),
        requested_at=now,
        completed_at=now,
        status="MATCH",
        risk_level="HIGH",
        matched=True,
        error_message=None,
    )
    screening_lifted = SimpleNamespace(
        id=uuid4(),
        requested_at=now,
        completed_at=now,
        status="MATCH",
        risk_level="HIGH",
        matched=True,
        error_message=None,
    )
    override = SimpleNamespace(
        id=uuid4(),
        created_at=now,
        requested_by=1,
        requested_by_email="admin@test.com",
        reason="Validación documental",
        screening_id=screening_lifted.id,
    )
    db = MagicMock()
    db.query.side_effect = [
        _QueryMock(all_result=[blocked, lifted]),
        _QueryMock(first_result=screening_blocked),
        _QueryMock(first_result=None),
        _QueryMock(first_result=screening_lifted),
        _QueryMock(first_result=override),
    ]

    result = compliance_report_service.list_restricted_clients_report(db, 10)

    assert len(result) == 2
    assert result[0]["report_status"] == "BLOQUEADO"
    assert result[1]["report_status"] == "LEVANTADA"
    assert result[1]["screening_matched"] is True


def test_compliance_override_history_returns_joined_rows():
    client = SimpleNamespace(identification_number="123", full_name="CLIENTE TEST")
    override = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        screening_id=uuid4(),
        requested_by=5,
        requested_by_email="user@test.com",
        reason="Revisión completada",
        created_at=datetime.now(UTC),
    )
    query = _QueryMock(all_result=[(override, client)])
    db = MagicMock()
    db.query.return_value = query

    result = compliance_report_service.list_compliance_override_history(db, 10)

    assert len(result) == 1
    assert result[0]["identification_number"] == "123"
    assert result[0]["requested_by_email"] == "user@test.com"
    assert result[0]["reason"] == "Revisión completada"


def test_normalize_screening_text_and_similarity_helpers():
    assert screening_provider.normalize_screening_text("José  Pérez!") == "JOSE PEREZ"
    assert screening_provider.normalize_screening_text(None) == ""
    assert screening_provider._similarity("ABC", "ABC") == 1.0
    assert screening_provider._similarity("", "ABC") == 0.0


def test_parse_ofac_sdn_valid_entry_and_invalid_entry():
    xml = b"""
    <sdnList>
      <sdnEntry>
        <uid>123</uid><sdnType>individual</sdnType>
        <firstName>Jose</firstName><lastName>Perez</lastName>
        <aka><firstName>Juan</firstName><lastName>Lopez</lastName></aka>
        <idList><id><idNumber>ID-123</idNumber></id></idList>
      </sdnEntry>
      <sdnEntry><uid>456</uid></sdnEntry>
    </sdnList>
    """
    result = screening_provider._parse_ofac_sdn(xml)
    assert result[0]["external_id"] == "123"
    assert result[0]["entry_type"] == "INDIVIDUAL"
    assert result[0]["name"] == "Jose Perez"
    assert result[0]["aliases"] == ["Juan Lopez"]
    assert result[0]["identification_numbers"] == ["ID-123"]

    with pytest.raises(ValueError, match="no contiene registros"):
        screening_provider._parse_ofac_sdn(b"<sdnList />")


def test_sync_all_screening_lists_reports_success_and_failure():
    db = MagicMock()
    successful = {"source": "OFAC_SDN", "status": "SUCCESS"}
    with patch.dict(
        screening_provider.SCREENING_LIST_PROVIDERS,
        {"OK": lambda _db: successful},
        clear=True,
    ):
        result = screening_provider.sync_all_screening_lists(db)
        assert result["status"] == "SUCCESS"
        assert result["successful_sources"] == 1

    def failing(_db):
        raise RuntimeError("fuente caída")

    with patch.dict(
        screening_provider.SCREENING_LIST_PROVIDERS,
        {"BAD": failing},
        clear=True,
    ):
        result = screening_provider.sync_all_screening_lists(db)
        assert result["status"] == "ERROR"
        assert result["failed_sources"] == 1
