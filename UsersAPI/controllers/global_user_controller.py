from sqlalchemy.orm import Session

from ..models import GlobalUserDB
from ..schemas.global_user import GlobalSuperCreate, GlobalSuperUpdate
from ..services.global_user_service import (
    create_global_super,
    get_global_super,
    list_global_supers,
    update_global_super,
)
from ..services.super_mfa_service import verify_super_mfa_otp
from ..services.super_tenant_service import require_super_user


def listar_global_supers(db: Session, current_user):
    require_super_user(current_user)
    return list_global_supers(db)


def obtener_global_super(super_id: int, db: Session, current_user):
    require_super_user(current_user)
    return get_global_super(super_id, db)


def crear_global_super(
    datos: GlobalSuperCreate,
    otp: str,
    db: Session,
    current_user,
):
    return create_global_super(
        datos=datos,
        otp=otp,
        db=db,
        current_user=current_user,
    )


def actualizar_global_super(
    super_id: int,
    datos: GlobalSuperUpdate,
    otp: str,
    db: Session,
    current_user,
):
    return update_global_super(
        super_id=super_id,
        datos=datos,
        otp=otp,
        db=db,
        current_user=current_user,
    )
