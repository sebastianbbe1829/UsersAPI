from datetime import datetime, timezone

import pyotp
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import GlobalUserDB
from ..schemas.global_user import (
    GlobalSuperCreate,
    GlobalSuperCreateResponse,
    GlobalSuperUpdate,
)
from .global_auth_service import _decrypt_mfa_secret, _encrypt_mfa_secret
from .password_service import get_password_hash
from .super_mfa_service import verify_super_mfa_otp
from .super_tenant_service import require_super_user


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def list_global_supers(db: Session):
    return (
        db.query(GlobalUserDB)
        .filter(GlobalUserDB.is_superuser.is_(True))
        .order_by(GlobalUserDB.id)
        .all()
    )


def get_global_super(super_id: int, db: Session):
    user = (
        db.query(GlobalUserDB)
        .filter(
            GlobalUserDB.id == super_id,
            GlobalUserDB.is_superuser.is_(True),
        )
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario SUPER no encontrado.",
        )
    return user


def create_global_super(
    datos: GlobalSuperCreate,
    otp: str,
    db: Session,
    current_user,
):
    actor = require_super_user(current_user)
    verify_super_mfa_otp(actor, otp)

    email = str(datos.email).strip().lower()
    existing = db.query(GlobalUserDB).filter(GlobalUserDB.email == email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya está registrado como usuario global.",
        )

    now = _now()
    secret = pyotp.random_base32()
    user = GlobalUserDB(
        email=email,
        password_hash=get_password_hash(datos.password),
        is_active=True,
        is_superuser=True,
        mfa_enabled=True,
        mfa_secret_encrypted=_encrypt_mfa_secret(secret),
        mfa_verified_at=None,
        session_id=None,
        last_login_at=None,
        last_login_ip=None,
        created_at=now,
        created_by=actor.email,
        updated_at=now,
        updated_by=actor.email,
    )

    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya está registrado como usuario global.",
        ) from exc

    provisioning_uri = pyotp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name="UsersAPI",
    )

    logger.info(
        "Usuario SUPER creado por SUPER actor=%s target=%s",
        actor.email,
        user.email,
    )

    return GlobalSuperCreateResponse(
        **{
            field: getattr(user, field)
            for field in GlobalSuperCreateResponse.model_fields
            if field != "provisioning_uri"
        },
        provisioning_uri=provisioning_uri,
    )


def verify_global_super_mfa(
    super_id: int,
    actor_otp: str,
    target_otp: str,
    db: Session,
    current_user,
):
    actor = require_super_user(current_user)
    verify_super_mfa_otp(actor, actor_otp)

    user = get_global_super(super_id, db)
    if not user.mfa_enabled or not user.mfa_secret_encrypted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario SUPER no tiene un enrolamiento MFA válido.",
        )

    if user.mfa_verified_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El MFA del usuario SUPER ya está verificado.",
        )

    secret = _decrypt_mfa_secret(user.mfa_secret_encrypted)
    if not pyotp.TOTP(secret).verify(target_otp, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código MFA del usuario SUPER inválido.",
        )

    now = _now()
    user.mfa_verified_at = now
    user.updated_at = now
    user.updated_by = actor.email
    db.add(user)
    db.flush()

    logger.info(
        "MFA de usuario SUPER verificado por SUPER actor=%s target=%s target_id=%s",
        actor.email,
        user.email,
        user.id,
    )
    return user


def update_global_super(
    super_id: int,
    datos: GlobalSuperUpdate,
    otp: str,
    db: Session,
    current_user,
):
    actor = require_super_user(current_user)
    verify_super_mfa_otp(actor, otp)

    user = get_global_super(super_id, db)

    if datos.email is None and datos.password is None and datos.is_active is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe indicar al menos un campo para actualizar.",
        )

    if datos.email is not None:
        email = str(datos.email).strip().lower()
        existing = (
            db.query(GlobalUserDB)
            .filter(
                GlobalUserDB.email == email,
                GlobalUserDB.id != user.id,
            )
            .first()
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El correo ya está registrado como usuario global.",
            )
        user.email = email

    if datos.password is not None:
        user.password_hash = get_password_hash(datos.password)

    if datos.is_active is not None:
        if not datos.is_active and user.is_active:
            active_supers = (
                db.query(GlobalUserDB)
                .filter(
                    GlobalUserDB.is_superuser.is_(True),
                    GlobalUserDB.is_active.is_(True),
                )
                .count()
            )
            if active_supers <= 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No es posible desactivar el último usuario SUPER activo.",
                )

        user.is_active = datos.is_active
        if not datos.is_active:
            user.session_id = None

    user.updated_at = _now()
    user.updated_by = actor.email
    db.add(user)

    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No fue posible actualizar el usuario SUPER.",
        ) from exc

    logger.info(
        "Usuario SUPER actualizado por SUPER actor=%s target=%s target_id=%s",
        actor.email,
        user.email,
        user.id,
    )
    return user
