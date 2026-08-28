import pyotp
from fastapi import HTTPException, status

from ..models import GlobalUserDB
from .global_auth_service import _decrypt_mfa_secret


def verify_super_mfa_otp(
    user: GlobalUserDB,
    otp: str,
) -> None:
    if not user.is_active or not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene privilegios SUPER",
        )

    if not user.mfa_enabled or not user.mfa_verified_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El MFA del usuario SUPER no está verificado",
        )

    if not user.mfa_secret_encrypted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="El usuario SUPER no tiene MFA configurado",
        )

    secret = _decrypt_mfa_secret(user.mfa_secret_encrypted)

    if not pyotp.TOTP(secret).verify(otp, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código MFA inválido",
        )
