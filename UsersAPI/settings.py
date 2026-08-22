import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(
    Path(__file__).resolve().parents[1] / ".env",
    override=True,
)


@dataclass(frozen=True)
class Settings:
    secret_key: str = os.getenv("SECRET_KEY", "change-me")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))

    # ========================================================
    # DATABASE
    # ========================================================

    database_url: str = os.getenv("DATABASE_URL", "")
    bootstrap_database_url: str = os.getenv("BOOTSTRAP_DATABASE_URL", "")
    database_admin_url: str = os.getenv("DATABASE_ADMIN_URL", "")

    # ========================================================
    # BOOTSTRAP
    # ========================================================

    bootstrap_key: str = os.getenv("BOOTSTRAP_KEY", "")

    # ========================================================
    # SUPER
    # ========================================================

    super_bootstrap_secret: str = os.getenv("SUPER_BOOTSTRAP_SECRET", "")

    # Clave Fernet para cifrar el secreto TOTP del SUPER.
    super_mfa_encryption_key: str = os.getenv(
        "SUPER_MFA_ENCRYPTION_KEY",
        "",
    )


settings = Settings()
