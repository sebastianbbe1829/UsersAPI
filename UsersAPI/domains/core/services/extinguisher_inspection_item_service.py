from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import ExtinguisherInspectionItemDB
from ..repositories.extinguisher_inspection_item_repository import (
    ExtinguisherInspectionItemRepository,
)
from ..schemas.extinguisher_inspection_item import (
    ExtinguisherInspectionItemCreate,
    ExtinguisherInspectionItemUpdate,
)


def list_inspection_items(db: Session):
    return ExtinguisherInspectionItemRepository(db).get_all(include_inactive=True)


def get_inspection_item(item_id: int, db: Session):
    item = ExtinguisherInspectionItemRepository(db).get_by_id(item_id, include_inactive=True)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ítem de revisión no encontrado",
        )
    return item


def create_inspection_item(datos: ExtinguisherInspectionItemCreate, db: Session):
    repo = ExtinguisherInspectionItemRepository(db)
    code = datos.code.strip().upper()
    name = datos.name.strip()

    if not code or not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código y nombre son obligatorios",
        )

    if repo.get_by_code(code):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El código del ítem de revisión ya existe",
        )

    item = ExtinguisherInspectionItemDB(
        code=code,
        name=name,
        active=True,
        display_order=datos.display_order,
    )
    try:
        repo.add(item)
        db.refresh(item)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El código del ítem de revisión ya existe",
        ) from exc
    return item


def update_inspection_item(
    item_id: int,
    datos: ExtinguisherInspectionItemUpdate,
    db: Session,
):
    repo = ExtinguisherInspectionItemRepository(db)
    item = repo.get_by_id(item_id, include_inactive=True)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ítem de revisión no encontrado",
        )

    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay datos para actualizar",
        )

    if "code" in cambios:
        code = cambios["code"].strip().upper()
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El código es obligatorio",
            )
        existente = repo.get_by_code(code)
        if existente is not None and existente.id != item.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El código del ítem de revisión ya existe",
            )
        cambios["code"] = code

    if "name" in cambios:
        name = cambios["name"].strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre es obligatorio",
            )
        cambios["name"] = name

    for campo, valor in cambios.items():
        setattr(item, campo, valor)
    item.updated_at = datetime.now()

    try:
        repo.update(item)
        db.refresh(item)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El código del ítem de revisión ya existe",
        ) from exc
    return item


def delete_inspection_item(item_id: int, db: Session):
    repo = ExtinguisherInspectionItemRepository(db)
    item = repo.get_by_id(item_id, include_inactive=True)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ítem de revisión no encontrado",
        )
    if not item.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ítem de revisión ya está inactivo",
        )

    item.active = False
    item.updated_at = datetime.now()
    repo.update(item)
    return item
