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

    bootstrap_tenant_key: str = os.getenv("BOOTSTRAP_TENANT_KEY", "")

    # ========================================================
    # SUPER
    # ========================================================

    super_bootstrap_secret: str = os.getenv("SUPER_BOOTSTRAP_SECRET", "")
    super_mfa_encryption_key: str = os.getenv(
        "SUPER_MFA_ENCRYPTION_KEY",
        "",
    )

    # ========================================================
    # EMAIL
    # ========================================================

    brevo_api_key: str = os.getenv("BREVO_API_KEY", "")
    email_from: str = os.getenv("EMAIL_FROM", "")
    email_from_name: str = os.getenv("EMAIL_FROM_NAME", "UsersAPI")
    email_key: str = os.getenv("EMAIL_KEY", "")
    frontend_url: str = os.getenv("FRONTEND_URL", "")
    backend_url: str = os.getenv("BACKEND_URL", "")
    api_email_url : str = os.getenv("API_EMAIL_URL", "")

    # ========================================================
    # WHATSAPP
    # ========================================================

    whatsapp_token: str = os.getenv("WHATSAPP_TOKEN", "")
    whatsapp_phone_id: str = os.getenv("WHATSAPP_PHONE_ID", "")
    whatsapp_mode: str = os.getenv("WHATSAPP_MODE", "template")
    whatsapp_api_url : str = os.getenv("WHATSAPP_API_URL", "")


settings = Settings()
