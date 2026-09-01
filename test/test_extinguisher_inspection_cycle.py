from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from UsersAPI.schemas.extinguisher_inspection import ExtinguisherInspectionCreate
from UsersAPI.services import extinguisher_inspection_service


class FakeSession:
    def __init__(self):
        self.added = []

    def add(self, instance):
        self.added.append(instance)

    def flush(self):
        pass

    def refresh(self, instance):
        pass


class FakeInspectionRepository:
    def __init__(self, db):
        self.db = db
        self.extinguisher = None
        self.inspection_id = 100
        self.created_inspections = []

    def get_extinguisher_for_update(self, extinguisher_id, tenant_id):
        return self.extinguisher

    def add(self, inspection):
        inspection.id = self.inspection_id
        self.inspection_id += 1
        self.created_inspections.append(inspection)
        self.db.add(inspection)
        self.db.flush()
        return inspection


class FakeItemRepository:
    def __init__(self, db):
        self.items = [SimpleNamespace(id=item_id) for item_id in range(1, 8)]

    def get_all_active(self):
        return self.items


def make_payload(hydrostatic=False):
    return ExtinguisherInspectionCreate(
        inspection_date=date(2026, 9, 1),
        result="APTO",
        observations="Sin novedades",
        hydrostatic_test_performed=hydrostatic,
        hydrostatic_test_date=date(2026, 9, 1) if hydrostatic else None,
        next_hydrostatic_test_date=date(2031, 9, 1) if hydrostatic else None,
        items=[
            {"inspection_item_id": item_id, "result": "GOOD"}
            for item_id in range(1, 8)
        ],
    )


def setup_service(db, extinguisher):
    inspection_repo = FakeInspectionRepository(db)
    inspection_repo.extinguisher = extinguisher
    item_repo = FakeItemRepository(db)
    return inspection_repo, item_repo


def test_four_normal_inspections_increment_counter_and_number():
    db = FakeSession()
    extinguisher = SimpleNamespace(
        id=10, tenant_id=1, inspections_since_hydrostatic_test=0,
        inspection_cycle=1, last_hydrostatic_test_date=None, updated_at=None,
    )
    inspection_repo, item_repo = setup_service(db, extinguisher)
    user_tenant = SimpleNamespace(tenant_id=1, id=99)

    with (
        patch.object(extinguisher_inspection_service, "ExtinguisherInspectionRepository", return_value=inspection_repo),
        patch.object(extinguisher_inspection_service, "ExtinguisherInspectionItemRepository", return_value=item_repo),
    ):
        for expected_number in range(1, 5):
            inspection = extinguisher_inspection_service.create_inspection(10, make_payload(), db, user_tenant)
            assert inspection.inspection_number == expected_number
            assert inspection.inspection_cycle == 1
            assert extinguisher.inspections_since_hydrostatic_test == expected_number

    assert len(inspection_repo.created_inspections) == 4


def test_fifth_inspection_without_hydrostatic_is_rejected_and_counter_stays_at_four():
    db = FakeSession()
    extinguisher = SimpleNamespace(
        id=10, tenant_id=1, inspections_since_hydrostatic_test=4,
        inspection_cycle=1, last_hydrostatic_test_date=None, updated_at=None,
    )
    inspection_repo, item_repo = setup_service(db, extinguisher)
    user_tenant = SimpleNamespace(tenant_id=1, id=99)

    with (
        patch.object(extinguisher_inspection_service, "ExtinguisherInspectionRepository", return_value=inspection_repo),
        patch.object(extinguisher_inspection_service, "ExtinguisherInspectionItemRepository", return_value=item_repo),
    ):
        with pytest.raises(HTTPException) as exc_info:
            extinguisher_inspection_service.create_inspection(10, make_payload(), db, user_tenant)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "La quinta revisión requiere obligatoriamente una prueba hidrostática"
    assert extinguisher.inspections_since_hydrostatic_test == 4
    assert len(inspection_repo.created_inspections) == 0


def test_fifth_inspection_with_hydrostatic_resets_counter_and_starts_new_cycle():
    db = FakeSession()
    hydrostatic_date = date(2026, 9, 1)
    next_hydrostatic_date = date(2031, 9, 1)
    extinguisher = SimpleNamespace(
        id=10, tenant_id=1, inspections_since_hydrostatic_test=4,
        inspection_cycle=1, last_hydrostatic_test_date=None, updated_at=None,
    )
    inspection_repo, item_repo = setup_service(db, extinguisher)
    user_tenant = SimpleNamespace(tenant_id=1, id=99)

    with (
        patch.object(extinguisher_inspection_service, "ExtinguisherInspectionRepository", return_value=inspection_repo),
        patch.object(extinguisher_inspection_service, "ExtinguisherInspectionItemRepository", return_value=item_repo),
    ):
        inspection = extinguisher_inspection_service.create_inspection(
            10, make_payload(hydrostatic=True), db, user_tenant
        )

    assert inspection.inspection_number == 5
    assert inspection.inspection_cycle == 1
    assert inspection.hydrostatic_test_performed is True
    assert inspection.hydrostatic_test_date == hydrostatic_date
    assert inspection.next_hydrostatic_test_date == next_hydrostatic_date
    assert extinguisher.inspections_since_hydrostatic_test == 0
    assert extinguisher.inspection_cycle == 2
    assert extinguisher.last_hydrostatic_test_date == hydrostatic_date
    assert len(inspection_repo.created_inspections) == 1


def test_next_inspection_after_hydrostatic_is_number_one_of_new_cycle():
    db = FakeSession()
    extinguisher = SimpleNamespace(
        id=10, tenant_id=1, inspections_since_hydrostatic_test=0,
        inspection_cycle=2, last_hydrostatic_test_date=date(2026, 9, 1), updated_at=None,
    )
    inspection_repo, item_repo = setup_service(db, extinguisher)
    user_tenant = SimpleNamespace(tenant_id=1, id=99)

    with (
        patch.object(extinguisher_inspection_service, "ExtinguisherInspectionRepository", return_value=inspection_repo),
        patch.object(extinguisher_inspection_service, "ExtinguisherInspectionItemRepository", return_value=item_repo),
    ):
        inspection = extinguisher_inspection_service.create_inspection(10, make_payload(), db, user_tenant)

    assert inspection.inspection_number == 1
    assert inspection.inspection_cycle == 2
    assert extinguisher.inspections_since_hydrostatic_test == 1


def test_hydrostatic_cycle_does_not_delete_historical_inspections():
    db = FakeSession()
    historical_inspections = [
        SimpleNamespace(id=1, inspection_number=1, inspection_cycle=1),
        SimpleNamespace(id=2, inspection_number=2, inspection_cycle=1),
        SimpleNamespace(id=3, inspection_number=3, inspection_cycle=1),
        SimpleNamespace(id=4, inspection_number=4, inspection_cycle=1),
    ]
    extinguisher = SimpleNamespace(
        id=10, tenant_id=1, inspections_since_hydrostatic_test=4,
        inspection_cycle=1, last_hydrostatic_test_date=None, updated_at=None,
    )
    inspection_repo, item_repo = setup_service(db, extinguisher)
    inspection_repo.created_inspections.extend(historical_inspections)
    user_tenant = SimpleNamespace(tenant_id=1, id=99)

    with (
        patch.object(extinguisher_inspection_service, "ExtinguisherInspectionRepository", return_value=inspection_repo),
        patch.object(extinguisher_inspection_service, "ExtinguisherInspectionItemRepository", return_value=item_repo),
    ):
        extinguisher_inspection_service.create_inspection(10, make_payload(hydrostatic=True), db, user_tenant)

    assert [item.id for item in inspection_repo.created_inspections[:4]] == [1, 2, 3, 4]
    assert len(inspection_repo.created_inspections) == 5
    assert extinguisher.inspections_since_hydrostatic_test == 0
