from datetime import date

import pytest

from scripts.database.import_extinguishers_initial import (
    ITEM_COLUMNS,
    MigrationError,
    catalog_key,
    get_item_result,
    get_overall_result,
    get_revision_number,
    is_marked,
    parse_date,
)


def test_revision_number_comes_from_single_marked_column():
    row = {
        "REVISION 1": "",
        "REVISION 2": "",
        "REVISION 3": "",
        "REVISION 4": "X",
    }

    assert get_revision_number(row, 2) == 4


def test_revision_number_requires_exactly_one_mark():
    row = {
        "REVISION 1": "X",
        "REVISION 2": "X",
        "REVISION 3": "",
        "REVISION 4": "",
    }

    with pytest.raises(MigrationError):
        get_revision_number(row, 2)


def test_item_result_maps_good_bad_and_unknown():
    assert get_item_result({"GOOD": "X", "BAD": ""}, "GOOD", "BAD", 2) == "GOOD"
    assert get_item_result({"GOOD": "", "BAD": "X"}, "GOOD", "BAD", 2) == "BAD"
    assert get_item_result({"GOOD": "", "BAD": ""}, "GOOD", "BAD", 2) == "NA"


def test_item_result_rejects_good_and_bad_at_same_time():
    with pytest.raises(MigrationError):
        get_item_result({"GOOD": "X", "BAD": "X"}, "GOOD", "BAD", 2)


def test_overall_result_requires_all_items_to_be_known_good():
    assert get_overall_result(["GOOD", "NA", "BAD"]) == "REQUIERE_MANTENIMIENTO"
    assert get_overall_result(["GOOD"] * len(ITEM_COLUMNS)) == "APTO"
    assert get_overall_result(["NA"] * len(ITEM_COLUMNS)) == "REQUIERE_MANTENIMIENTO"


def test_parse_date_accepts_expected_formats():
    assert parse_date("31/08/2026", "fecha", 2) == date(2026, 8, 31)
    assert parse_date("2026-08-31", "fecha", 2) == date(2026, 8, 31)
    assert parse_date("", "fecha", 2) is None


def test_catalog_key_handles_accents_and_punctuation():
    assert catalog_key("Polvo químico seco (PQS)") == "POLVO QUIMICO SECO PQS"
    assert catalog_key("Dióxido de carbono") == "DIOXIDO DE CARBONO"
    assert is_marked("x")
    assert is_marked("sí")
    assert not is_marked("")
