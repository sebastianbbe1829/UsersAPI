from unittest.mock import MagicMock, patch

from UsersAPI.domains.clients.services.screening_provider import (
    OFAC_CONSOLIDATED_CODE,
    OFAC_SDN_CODE,
    UN_CONSOLIDATED_CODE,
    SCREENING_LIST_PROVIDERS,
    _parse_source,
    sync_all_screening_lists,
)


def test_screening_provider_registers_all_required_sources():
    assert set(SCREENING_LIST_PROVIDERS) == {
        OFAC_SDN_CODE,
        OFAC_CONSOLIDATED_CODE,
        UN_CONSOLIDATED_CODE,
    }


def test_parse_ofac_source_supports_sdn_and_consolidated_codes():
    xml = b"""
    <sdnList>
      <sdnEntry>
        <uid>123</uid>
        <sdnType>Individual</sdnType>
        <firstName>JUAN</firstName>
        <lastName>PEREZ</lastName>
        <aka><firstName>JUANITO</firstName><lastName>PEREZ</lastName></aka>
        <idList><id><idType>National ID</idType><idNumber>999</idNumber></id></idList>
      </sdnEntry>
    </sdnList>
    """

    for source_code in (OFAC_SDN_CODE, OFAC_CONSOLIDATED_CODE):
        entries = _parse_source(source_code, xml)
        assert entries[0]["external_id"] == "123"
        assert entries[0]["name"] == "JUAN PEREZ"
        assert "JUANITO PEREZ" in entries[0]["aliases"]
        assert "999" in entries[0]["identification_numbers"]


def test_parse_un_consolidated_source():
    xml = b"""
    <CONSOLIDATED_LIST>
      <INDIVIDUAL>
        <REFERENCE_NUMBER>QDi.001</REFERENCE_NUMBER>
        <FIRST_NAME>JUAN</FIRST_NAME>
        <SECOND_NAME>PEREZ</SECOND_NAME>
        <ALIAS_NAME><QUALITY>Good</QUALITY><ALIAS_NAME>JUANITO</ALIAS_NAME></ALIAS_NAME>
        <IDENTIFICATION_NUMBER>ABC123</IDENTIFICATION_NUMBER>
      </INDIVIDUAL>
    </CONSOLIDATED_LIST>
    """

    entries = _parse_source(UN_CONSOLIDATED_CODE, xml)

    assert entries[0]["external_id"] == "QDi.001"
    assert entries[0]["name"] == "JUAN PEREZ"
    assert "ABC123" in entries[0]["identification_numbers"]


def test_sync_all_screening_lists_reports_three_sources():
    db = MagicMock()
    results = [
        {"source": OFAC_SDN_CODE, "status": "SUCCESS", "total": 10},
        {"source": OFAC_CONSOLIDATED_CODE, "status": "SUCCESS", "total": 20},
        {"source": UN_CONSOLIDATED_CODE, "status": "SUCCESS", "total": 30},
    ]

    with patch.dict(
        SCREENING_LIST_PROVIDERS,
        {
            OFAC_SDN_CODE: lambda _db: results[0],
            OFAC_CONSOLIDATED_CODE: lambda _db: results[1],
            UN_CONSOLIDATED_CODE: lambda _db: results[2],
        },
        clear=True,
    ):
        result = sync_all_screening_lists(db)

    assert result["status"] == "SUCCESS"
    assert result["total_sources"] == 3
    assert result["successful_sources"] == 3
    assert result["failed_sources"] == 0
    assert [item["source"] for item in result["sources"]] == [
        OFAC_SDN_CODE,
        OFAC_CONSOLIDATED_CODE,
        UN_CONSOLIDATED_CODE,
    ]


def test_sync_all_screening_lists_keeps_partial_error():
    db = MagicMock()

    with patch.dict(
        SCREENING_LIST_PROVIDERS,
        {
            OFAC_SDN_CODE: lambda _db: {
                "source": OFAC_SDN_CODE,
                "status": "SUCCESS",
                "total": 10,
            },
            OFAC_CONSOLIDATED_CODE: lambda _db: (_ for _ in ()).throw(
                RuntimeError("OFAC unavailable")
            ),
            UN_CONSOLIDATED_CODE: lambda _db: {
                "source": UN_CONSOLIDATED_CODE,
                "status": "SUCCESS",
                "total": 30,
            },
        },
        clear=True,
    ):
        result = sync_all_screening_lists(db)

    assert result["status"] == "PARTIAL_ERROR"
    assert result["total_sources"] == 3
    assert result["successful_sources"] == 2
    assert result["failed_sources"] == 1
    assert result["sources"][1]["source"] == OFAC_CONSOLIDATED_CODE
    assert result["sources"][1]["status"] == "ERROR"
