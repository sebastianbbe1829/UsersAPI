from typing import List

from fastapi import APIRouter, Depends, Header, Path, status
from sqlalchemy.orm import Session

from ..controllers import global_user_controller
from ..controllers.auth_controller import get_current_user
from ..database import get_bootstrap_db
from ..schemas import (
    GlobalSuperCreate,
    GlobalSuperCreateResponse,
    GlobalSuperRead,
    GlobalSuperUpdate,
)
from ..schemas.global_user import GlobalSuperMfaProvisioningResponse


global_user_routes = APIRouter(
    prefix="/global-users",
    tags=["Usuarios SUPER"],
)


@global_user_routes.get(
    "/supers",
    response_model=List[GlobalSuperRead],
    status_code=status.HTTP_200_OK,
    summary="Listar usuarios SUPER",
)
def listar_global_supers_route(
    db: Session = Depends(get_bootstrap_db),
    current_user=Depends(get_current_user),
):
    return global_user_controller.listar_global_supers(
        db=db,
        current_user=current_user,
    )


@global_user_routes.get(
    "/supers/{super_id}",
    response_model=GlobalSuperRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener usuario SUPER",
)
def obtener_global_super_route(
    super_id: int = Path(..., description="ID del usuario SUPER"),
    db: Session = Depends(get_bootstrap_db),
    current_user=Depends(get_current_user),
):
    return global_user_controller.obtener_global_super(
        super_id=super_id,
        db=db,
        current_user=current_user,
    )


@global_user_routes.get(
    "/supers/{super_id}/mfa-provisioning",
    response_model=GlobalSuperMfaProvisioningResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener datos de enrolamiento MFA de un usuario SUPER",
)
def obtener_global_super_mfa_provisioning_route(
    super_id: int = Path(..., description="ID del usuario SUPER"),
    db: Session = Depends(get_bootstrap_db),
    current_user=Depends(get_current_user),
):
    return global_user_controller.obtener_global_super_mfa_provisioning(
        super_id=super_id,
        db=db,
        current_user=current_user,
    )


@global_user_routes.post(
    "/supers",
    response_model=GlobalSuperCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario SUPER",
)
def crear_global_super_route(
    datos: GlobalSuperCreate,
    x_super_mfa_otp: str = Header(..., alias="X-Super-MFA-OTP"),
    db: Session = Depends(get_bootstrap_db),
    current_user=Depends(get_current_user),
):
    return global_user_controller.crear_global_super(
        datos=datos,
        otp=x_super_mfa_otp,
        db=db,
        current_user=current_user,
    )


@global_user_routes.patch(
    "/supers/{super_id}",
    response_model=GlobalSuperRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar usuario SUPER",
)
def actualizar_global_super_route(
    super_id: int = Path(..., description="ID del usuario SUPER"),
    datos: GlobalSuperUpdate = ...,
    x_super_mfa_otp: str = Header(..., alias="X-Super-MFA-OTP"),
    db: Session = Depends(get_bootstrap_db),
    current_user=Depends(get_current_user),
):
    return global_user_controller.actualizar_global_super(
        super_id=super_id,
        datos=datos,
        otp=x_super_mfa_otp,
        db=db,
        current_user=current_user,
    )
