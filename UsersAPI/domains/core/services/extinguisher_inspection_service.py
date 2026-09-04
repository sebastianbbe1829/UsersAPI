from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import ExtinguisherInspectionDB, ExtinguisherInspectionResultDB, UserTenantDB
from ..repositories.extinguisher_inspection_repository import (
    ExtinguisherInspectionItemRepository,
    ExtinguisherInspectionRepository,
)
from ..schemas.extinguisher_inspection import ExtinguisherInspectionCreate

VALID_INSPECTION_RESULTS = {"APTO", "REQUIERE_MANTENIMIENTO", "FUERA_DE_SERVICIO"}
VALID_ITEM_RESULTS = {"GOOD", "BAD", "NA"}
MAX_NORMAL_INSPECTIONS = 4


def list_inspection_items(db: Session):
    return ExtinguisherInspectionItemRepository(db).get_all_active()


def list_inspections(db: Session, tenant_id: int, extinguisher_id: int | None = None):
    return ExtinguisherInspectionRepository(db).get_all_by_tenant(tenant_id, extinguisher_id)


def get_inspection(inspection_id: int, db: Session, tenant_id: int):
    item = ExtinguisherInspectionRepository(db).get_by_id_and_tenant(inspection_id, tenant_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revisión no encontrada",
        )
    return item


def create_inspection(
    extinguisher_id: int,
    datos: ExtinguisherInspectionCreate,
    db: Session,
    user_tenant: UserTenantDB,
):
    tenant_id = user_tenant.tenant_id
    repo = ExtinguisherInspectionRepository(db)
    extinguisher = repo.get_extinguisher_for_update(extinguisher_id, tenant_id)
    if extinguisher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extintor no encontrado",
        )

    result = datos.result.strip().upper()
    if result not in VALID_INSPECTION_RESULTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado de revisión no válido",
        )

    item_repo = ExtinguisherInspectionItemRepository(db)
    active_items = item_repo.get_all_active()
    active_item_ids = {item.id for item in active_items}
    submitted_ids = [item.inspection_item_id for item in datos.items]

    if len(submitted_ids) != len(set(submitted_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede repetir un ítem de revisión",
        )
    if set(submitted_ids) != active_item_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La revisión debe incluir todos los ítems activos del catálogo",
        )
    if any(item.result.strip().upper() not in VALID_ITEM_RESULTS for item in datos.items):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resultado de ítem no válido",
        )

    current_count = extinguisher.inspections_since_hydrostatic_test
    hydrostatic_required = current_count >= MAX_NORMAL_INSPECTIONS

    if hydrostatic_required and not datos.hydrostatic_test_performed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La quinta revisión requiere obligatoriamente una prueba hidrostática",
        )

    inspection_number = current_count + 1
    if inspection_number > 5:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El ciclo de revisiones requiere prueba hidrostática",
        )

    hydrostatic_performed = datos.hydrostatic_test_performed
    inspection = ExtinguisherInspectionDB(
        tenant_id=tenant_id,
        extinguisher_id=extinguisher.id,
        inspection_date=datos.inspection_date,
        inspector_user_id=user_tenant.id,
        inspection_number=inspection_number,
        inspection_cycle=extinguisher.inspection_cycle,
        result=result,
        observations=datos.observations,
        hydrostatic_test_performed=hydrostatic_performed,
        hydrostatic_test_date=datos.hydrostatic_test_date,
        next_hydrostatic_test_date=datos.next_hydrostatic_test_date,
    )
    repo.add(inspection)

    for item in datos.items:
        db.add(
            ExtinguisherInspectionResultDB(
                inspection_id=inspection.id,
                inspection_item_id=item.inspection_item_id,
                result=item.result.strip().upper(),
                observation=item.observation,
            )
        )

    if hydrostatic_performed:
        extinguisher.inspections_since_hydrostatic_test = 0
        extinguisher.inspection_cycle += 1
        extinguisher.last_hydrostatic_test_date = datos.hydrostatic_test_date
        extinguisher.next_hydrostatic_test_date = datos.next_hydrostatic_test_date
    else:
        extinguisher.inspections_since_hydrostatic_test = current_count + 1

    extinguisher.updated_at = datetime.now()
    db.add(extinguisher)
    db.flush()
    db.refresh(inspection)
    return inspection
