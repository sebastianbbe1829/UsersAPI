"""Unit tests for client screening helpers."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from UsersAPI.domains.clients.services.screening_provider import (
    ScreeningProvider,
    _parse_ofac_sdn,
    normalize_screening_text,
    sync_all_screening_lists,
    sync_ofac_sdn,
)
from UsersAPI.domains.clients.services.screening_report_service import list_screenings
from UsersAPI.domains.clients.services.screening_service import screen_client


def _query_results(source_results, entry_results):
    db = MagicMock()
    source_query = db.query.return_value
    source_query.filter.return_value.all.return_value = source_results
    entry_query = MagicMock()
    entry_query.filter.return_value.all.return_value = entry_results
    db.query.side_effect = [source_query, entry_query]
    return db


def test_normalize_text_removes_accents_and_collapses_spaces():
    assert normalize_screening_text("  José   Pérez ") == "JOSE PEREZ"


def test_provider_matches_identification_number():
    source = SimpleNamespace(
        id="source-1",
        code="OFAC_SDN",
        name="OFAC SDN",
    )
    entry = SimpleNamespace(
        id="entry-1",
        source_id="source-1",
        external_id="123",
        entry_type="INDIVIDUAL",
        name="JUAN PEREZ",
        normalized_name="JUAN PEREZ",
        aliases=[],
        identification_numbers=["123"],
        nationality=None,
        date_of_birth=None,
        active=True,
        source=source,
    )
    db = _query_results([source], [entry])
    client = SimpleNamespace(
        identification_number="123",
        full_name="OTRO NOMBRE",
        person_type="NATURAL",
    )

    result = ScreeningProvider().screen(client, db)

    assert result.status == "MATCH"
    assert result.matched is True
    assert result.response["matches"][0]["external_id"] == "123"


def test_provider_returns_clear_when_no_match():
    source = SimpleNamespace(
        id="source-1",
        code="OFAC_SDN",
        name="OFAC SDN",
    )
    db = _query_results([source], [])
    client = SimpleNamespace(
        identification_number="123",
        full_name="JUAN PEREZ",
        person_type="NATURAL",
    )

    result = ScreeningProvider().screen(client, db)

    assert result.status == "CLEAR"
    assert result.response["matches"] == []


def test_provider_returns_pending_without_synced_sources():
    db = _query_results([], [])
    client = SimpleNamespace(
        identification_number="123",
        full_name="JUAN PEREZ",
        person_type="NATURAL",
    )

    result = ScreeningProvider().screen(client, db)

    assert result.status == "PENDING"


def test_screen_client_updates_client_on_clear():
    db = MagicMock()
    client = SimpleNamespace(
        id=uuid4(),
        tenant_id=10,
        status="ACTIVE",
        compliance_status="PENDING",
        is_listed=False,
        list_type=None,
    )
    provider_result = SimpleNamespace(
        status="CLEAR",
        risk_level="LOW",
        matched=False,
        list_type=None,
        response={"matches": []},
    )

    with patch(
        "UsersAPI.domains.clients.services.screening_service.ScreeningProvider"
    ) as provider:
        provider.return_value.screen.return_value = provider_result
        result = screen_client(client, db)

    assert result.status == "CLEAR"
    assert client.status == "ACTIVE"
    assert client.compliance_status == "CLEAR"
    assert client.is_listed is False


def test_screen_client_blocks_client_on_match():
    db = MagicMock()
    client = SimpleNamespace(
        id=uuid4(),
        tenant_id=10,
        status="ACTIVE",
        compliance_status="PENDING",
        is_listed=False,
        list_type=None,
    )
    provider_result = SimpleNamespace(
        status="MATCH",
        risk_level="HIGH",
        matched=True,
        list_type="OFAC_SDN",
        response={"matches": [{"external_id": "35784"}]},
    )

    with patch(
        "UsersAPI.domains.clients.services.screening_service.ScreeningProvider"
    ) as provider:
        provider.return_value.screen.return_value = provider_result
        result = screen_client(client, db)

    assert result.status == "MATCH"
    assert client.status == "BLOCKED"
    assert client.compliance_status == "MATCH"
    assert client.is_listed is True
    assert client.list_type == "OFAC_SDN"


def test_screen_client_records_error_without_raising():
    db = MagicMock()
    client = SimpleNamespace(
        id=uuid4(),
        tenant_id=10,
        status="ACTIVE",
        compliance_status="PENDING",
        is_listed=False,
        list_type=None,
    )

    with patch(
        "UsersAPI.domains.clients.services.screening_service.ScreeningProvider"
    ) as provider:
        provider.return_value.screen.side_effect = RuntimeError("provider error")
        result = screen_client(client, db)

    assert result.status == "ERROR"
    assert client.compliance_status == "ERROR"
    assert client.is_listed is False


def test_list_screenings_maps_query_results():
    db = MagicMock()
    screening = SimpleNamespace(
        id="screening-1",
        tenant_id=10,
        client_id="client-1",
        provider="INTERNAL_OFFICIAL",
        status="CLEAR",
        risk_level=None,
        matched=False,
        requested_at=None,
        completed_at=None,
        response={"matches": []},
        error_message=None,
    )
    client = SimpleNamespace(
        id=screening.client_id,
        identification_number="123",
        full_name="JUAN PEREZ",
        person_type="NATURAL",
        tenant_id=10,
        list_type=None,
    )
    query = db.query.return_value
    query = query.join.return_value
    query = query.filter.return_value
    query = query.order_by.return_value
    query.all.return_value = [(screening, client)]

    result = list_screenings(db, 10)

    assert len(result) == 1
    assert result[0]["full_name"] == "JUAN PEREZ"
    assert result[0]["provider"] == "INTERNAL_OFFICIAL"


def test_parse_ofac_sdn_reads_entity_alias_and_identification_number():
    xml = b"""
    <sdnList xmlns=\"urn:test\">
      <sdnEntry>
        <uid>123</uid>
        <sdnType>Individual</sdnType>
        <firstName>José</firstName>
        <lastName>Pérez</lastName>
        <aka><name>Jose Perez Alias</name></aka>
        <aka><name>Jose Perez Alias</name></aka>
        <idList><id><idNumber>CC-123</idNumber></id></idList>
      </sdnEntry>
      <sdnEntry><uid>missing-name</uid></sdnEntry>
    </sdnList>
    """

    entries = _parse_ofac_sdn(xml)

    assert len(entries) == 1
    assert entries[0]["external_id"] == "123"
    assert entries[0]["entry_type"] == "INDIVIDUAL"
    assert entries[0]["name"] == "José Pérez"
    assert entries[0]["normalized_name"] == "JOSE PEREZ"
    assert entries[0]["aliases"] == ["Jose Perez Alias"]
    assert entries[0]["identification_numbers"] == ["CC-123"]


def test_parse_ofac_sdn_rejects_empty_document():
    with pytest.raises(ValueError, match="no contiene registros procesables"):
        _parse_ofac_sdn(b"<sdnList />")


def test_sync_ofac_sdn_creates_updates_and_deactivates_entries():
    db = MagicMock()
    source = SimpleNamespace(
        id="source-1",
        code="OFAC_SDN",
        url="old-url",
        last_sync_status=None,
        last_sync_error=None,
    )
    updated = SimpleNamespace(external_id="1", active=False)
    stale = SimpleNamespace(external_id="stale", active=True)

    source_query = MagicMock()
    source_query.filter.return_value.one_or_none.return_value = source
    entry_query = MagicMock()
    entry_query.filter.return_value.all.return_value = [updated, stale]
    db.query.side_effect = [source_query, entry_query]

    parsed = [
        {
            "external_id": "1",
            "entry_type": "INDIVIDUAL",
            "name": "UPDATED",
            "normalized_name": "UPDATED",
            "aliases": [],
            "identification_numbers": ["1"],
            "raw_data": {"uid": "1"},
        },
        {
            "external_id": "2",
            "entry_type": "ENTITY",
            "name": "NEW",
            "normalized_name": "NEW",
            "aliases": [],
            "identification_numbers": [],
            "raw_data": {"uid": "2"},
        },
    ]
    response = MagicMock(content=b"xml")
    response.raise_for_status.return_value = None

    with (
        patch("UsersAPI.domains.clients.services.screening_provider.requests.get", return_value=response),
        patch("UsersAPI.domains.clients.services.screening_provider._parse_ofac_sdn", return_value=parsed),
    ):
        result = sync_ofac_sdn(db)

    assert result == {
        "source": "OFAC_SDN",
        "status": "SUCCESS",
        "total": 2,
        "created": 1,
        "updated": 1,
        "deactivated": 1,
    }
    assert source.url.endswith("SDN.XML")
    assert source.last_sync_status == "SUCCESS"
    assert source.last_sync_error is None
    assert updated.active is True
    assert stale.active is False
    db.commit.assert_called_once()


def test_sync_ofac_sdn_records_error_and_reraises():
    db = MagicMock()
    source = SimpleNamespace(
        id="source-1",
        code="OFAC_SDN",
        url="old-url",
        last_sync_status=None,
        last_sync_error=None,
    )
    source_query = MagicMock()
    source_query.filter.return_value.one_or_none.return_value = source
    db.query.return_value = source_query

    with patch(
        "UsersAPI.domains.clients.services.screening_provider.requests.get",
        side_effect=RuntimeError("network failure"),
    ):
        with pytest.raises(RuntimeError, match="network failure"):
            sync_ofac_sdn(db)

    assert source.last_sync_status == "ERROR"
    assert source.last_sync_error == "network failure"
    db.rollback.assert_called_once()
    assert db.commit.call_count == 1


def test_sync_all_screening_lists_returns_success_summary():
    db = MagicMock()
    provider = MagicMock(return_value={"source": "OFAC_SDN", "status": "SUCCESS"})

    with patch(
        "UsersAPI.domains.clients.services.screening_provider.SCREENING_LIST_PROVIDERS",
        {"OFAC_SDN": provider},
    ):
        result = sync_all_screening_lists(db)

    assert result["status"] == "SUCCESS"
    assert result["total_sources"] == 1
    assert result["successful_sources"] == 1
    assert result["failed_sources"] == 0


def test_sync_all_screening_lists_returns_partial_error_when_provider_fails():
    db = MagicMock()
    provider = MagicMock(side_effect=RuntimeError("source unavailable"))

    with patch(
        "UsersAPI.domains.clients.services.screening_provider.SCREENING_LIST_PROVIDERS",
        {"OFAC_SDN": provider},
    ):
        result = sync_all_screening_lists(db)

    assert result["status"] == "ERROR"
    assert result["total_sources"] == 1
    assert result["successful_sources"] == 0
    assert result["failed_sources"] == 1
    assert result["sources"][0]["error"] == "source unavailable"
