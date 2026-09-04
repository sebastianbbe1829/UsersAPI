from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import set_rls_tenant
from ..repositories.user_repository import UserRepository
from ..repositories.user_tenant_repository import UserTenantRepository
from .otp_service import generate_otp, validate_otp
from .user_service import activate_user


ACTIVATION_OTP_PURPOSE = "account_activation"


def _set_activation_tenant_context(
    token: str,
    db: Session,
) -> None:
    tenant_id = db.execute(
        text(
            """
            SELECT users_api.resolve_tenant_id_by_activation_token(
                :activation_token
            )
            """
        ),
        {
            "activation_token": token,
        },
    ).scalar()

    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de activación inválido",
        )

    set_rls_tenant(
        db,
        tenant_id,
    )


def _get_activation_context(
    dni: str,
    token: str,
    db: Session,
):
    _set_activation_tenant_context(token, db)

    user_tenant_repository = UserTenantRepository(db)
    user_repository = UserRepository(db)

    link = user_tenant_repository.get_by_activation_token(token)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de activación inválido",
        )

    usuario = user_repository.get_by_dni(dni)
    if usuario is None or link.user_id != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de activación inválido",
        )

    if link.status == 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario se encuentra eliminado",
        )

    if link.status == 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario ya se encuentra activo",
        )

    if not link.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario no tiene un correo electrónico registrado",
        )

    return usuario, link


def generate_activation_otp(
    dni: str,
    token: str,
    db: Session,
) -> datetime:
    usuario, link = _get_activation_context(dni, token, db)

    return generate_otp(
        db,
        destination=link.email,
        purpose=ACTIVATION_OTP_PURPOSE,
        subject="Código para activar tu cuenta",
        message=(
            f"Hola {usuario.name}, hemos generado un código de verificación "
            "para completar la activación de tu cuenta."
        ),
    )


def validate_activation_otp(
    dni: str,
    token: str,
    code: str,
    db: Session,
) -> bool:
    _, link = _get_activation_context(dni, token, db)

    valid = validate_otp(
        db,
        destination=link.email,
        purpose=ACTIVATION_OTP_PURPOSE,
        code=code,
    )

    if not valid:
        return False

    activate_user(
        dni=dni,
        token=token,
        db=db,
    )

    return True
