from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import ExtinguisherTypeDB
from ..repositories.extinguisher_type_repository import ExtinguisherTypeRepository
from ..schemas import ExtinguisherTypeCreate, ExtinguisherTypeUpdate


def list_extinguisher_types(db: Session):
    return ExtinguisherTypeRepository(db).get_all()


def create_extinguisher_type(datos: ExtinguisherTypeCreate, db: Session):
    repo = ExtinguisherTypeRepository(db)
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
            detail="El tipo de extintor ya existe",
        )

    item = ExtinguisherTypeDB(code=code, name=name, active=True)
    try:
        repo.add(item)
        db.refresh(item)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El tipo de extintor ya existe",
        ) from exc
    return item


def update_extinguisher_type(type_id: int, datos: ExtinguisherTypeUpdate, db: Session):
    repo = ExtinguisherTypeRepository(db)
    item = repo.get_by_id(type_id, include_inactive=True)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de extintor no encontrado",
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
                detail="El tipo de extintor ya existe",
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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El tipo de extintor ya existe",
        ) from exc
    return item


def delete_extinguisher_type(type_id: int, db: Session):
    repo = ExtinguisherTypeRepository(db)
    item = repo.get_by_id(type_id, include_inactive=True)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de extintor no encontrado",
        )
    if not item.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tipo de extintor ya está inactivo",
        )

    item.active = False
    item.updated_at = datetime.now()
    repo.update(item)
    return item
