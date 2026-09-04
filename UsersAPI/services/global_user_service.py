import base64
import io
from datetime import datetime, timezone

import pyotp
import qrcode
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
from ..util.email_utils import send_email
from .global_auth_service import _decrypt_mfa_secret, _encrypt_mfa_secret
from .password_service import get_password_hash
from .super_mfa_service import verify_super_mfa_otp
from .super_tenant_service import require_super_user


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _build_qr(provisioning_uri: str):
    qr = qrcode.QRCode(box_size=8, border=4)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    return qr


def _qr_attachment(provisioning_uri: str) -> dict[str, str]:
    qr = _build_qr(provisioning_uri)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return {
        "name": "mfa_qr.png",
        "content": base64.b64encode(buffer.getvalue()).decode("ascii"),
    }


def _qr_html(provisioning_uri: str) -> str:
    """Renderiza el QR como tabla HTML con celdas de tamaño fijo para clientes de correo."""
    qr = _build_qr(provisioning_uri)
    matrix = qr.get_matrix()
    pixel_size = 4
    size = len(matrix)
    table_size = size * pixel_size
    rows = []

    for row in matrix:
        cells = []
        for dark in row:
            background = "#000000" if dark else "#ffffff"
            cells.append(
                f'<td width="{pixel_size}" height="{pixel_size}" '
                'style="width:4px;height:4px;padding:0;margin:0;'
                'font-size:0;line-height:0;mso-line-height-rule:exactly;'
                f'background-color:{background};">'
                f'<div style="width:{pixel_size}px;height:{pixel_size}px;'
                f'background-color:{background};font-size:0;line-height:0;">'
                '</div></td>'
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")

    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'width="{table_size}" height="{table_size}" '
        f'style="border-collapse:collapse;border-spacing:0;margin:0 auto;'
        f'width:{table_size}px;height:{table_size}px;background:#ffffff;">'
        + "".join(rows)
        + "</table>"
    )


def list_global_supers(db: Session, current_user=None):
    supers = (
        db.query(GlobalUserDB)
        .filter(GlobalUserDB.is_superuser.is_(True))
        .order_by(GlobalUserDB.id)
        .all()
    )

    if (
        isinstance(current_user, GlobalUserDB)
        and current_user.is_superuser
        and current_user.is_active
        and all(user.id != current_user.id for user in supers)
    ):
        supers.insert(0, current_user)

    return supers


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


def get_global_super_mfa_provisioning(super_id: int, db: Session):
    user = get_global_super(super_id, db)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No es posible visualizar el MFA de un usuario SUPER inactivo.",
        )

    if not user.mfa_enabled or not user.mfa_secret_encrypted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario SUPER no tiene un enrolamiento MFA válido.",
        )

    secret = _decrypt_mfa_secret(user.mfa_secret_encrypted)
    provisioning_uri = pyotp.TOTP(secret).provisioning_uri(
        name=user.email,
        issuer_name="UsersAPI",
    )

    return {
        "id": user.id,
        "email": user.email,
        "provisioning_uri": provisioning_uri,
    }


def create_global_super(
    datos: GlobalSuperCreate,
    otp: str,
    db: Session,
    actor,
):
    actor = require_super_user(actor)
    verify_super_mfa_otp(actor, otp)

    email = str(datos.email).strip().lower()
    dni = datos.dni.strip()

    existing = db.query(GlobalUserDB).filter(GlobalUserDB.email == email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya está registrado como usuario global.",
        )

    existing_dni = db.query(GlobalUserDB).filter(GlobalUserDB.dni == dni).first()
    if existing_dni is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El DNI ya está registrado como usuario SUPER.",
        )

    now = _now()
    secret = pyotp.random_base32()
    user = GlobalUserDB(
        dni=dni,
        name=datos.name.strip(),
        phone=datos.phone.strip(),
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
            detail="El correo o DNI ya está registrado como usuario SUPER.",
        ) from exc

    provisioning_uri = pyotp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name="UsersAPI",
    )

    email_sent = False
    if datos.send_email:
        send_email(
            recipient=email,
            subject="Tu cuenta SUPER de UsersAPI",
            message=(
                f"Hola {user.name},\n\n"
                "Tu cuenta de usuario SUPER ha sido creada. "
                "Adjuntamos el código QR para configurar tu autenticación MFA.\n\n"
                "1. Escanea el QR con Google Authenticator, Microsoft Authenticator "
                "o una aplicación compatible.\n"
                "2. Ingresa con tu correo y contraseña inicial.\n"
                "3. En tu primer inicio de sesión introduce el código de 6 dígitos "
                "generado por tu Authenticator.\n\n"
                "Por seguridad, no compartas el QR ni el código MFA."
            ),
            template="super_invitation",
            tenant_name="UsersAPI",
            qr_html=_qr_html(provisioning_uri),
            attachments=[_qr_attachment(provisioning_uri)],
        )
        email_sent = True

    logger.info(
        "Usuario SUPER creado por SUPER actor=%s target=%s dni=%s email_sent=%s",
        actor.email,
        user.email,
        user.dni,
        email_sent,
    )

    return GlobalSuperCreateResponse(
        **{
            field: getattr(user, field)
            for field in GlobalSuperCreateResponse.model_fields
            if field not in {"provisioning_uri", "email_sent"}
        },
        provisioning_uri=provisioning_uri,
        email_sent=email_sent,
    )


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

    if (
        datos.name is None
        and datos.phone is None
        and datos.password is None
        and datos.is_active is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe indicar al menos un campo para actualizar.",
        )

    if datos.name is not None:
        user.name = datos.name.strip()

    if datos.phone is not None:
        user.phone = datos.phone.strip()

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
