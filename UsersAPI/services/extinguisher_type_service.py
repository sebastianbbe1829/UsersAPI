from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import ExtinguisherTypeDB
from ..repositories.extinguisher_type_repository import ExtinguisherTypeRepository
from ..schemas import ExtinguisherTypeCreate


def list_extinguisher_types(db: Session):
    return ExtinguisherTypeRepository(db).get_all()


def create_extinguisher_type(datos: ExtinguisherTypeCreate, db: Session):
    repo = ExtinguisherTypeRepository(db)
    code = datos.code.strip().upper()
    name = datos.name.strip()

    if not code or not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código y nombre son obligatorios")

    if repo.get_by_code(code):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El tipo de extintor ya existe")

    item = ExtinguisherTypeDB(code=code, name=name, active=True)
    try:
        repo.add(item)
        db.refresh(item)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El tipo de extintor ya existe") from exc
    return item
