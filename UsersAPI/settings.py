import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()

if APP_ENV == "development":
    load_dotenv(BASE_DIR / ".env", override=False)
elif APP_ENV == "test":
    load_dotenv(BASE_DIR / ".env.test", override=False)
elif APP_ENV == "production":
    pass
else:
    raise RuntimeError("APP_ENV inválido. Valores permitidos: development, test, production.")


@dataclass(frozen=True)
class Settings:
    secret_key: str = os.getenv("SECRET_KEY", "change-me")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    session_idle_timeout_minutes: int = int(os.getenv("SESSION_IDLE_TIMEOUT_MINUTES", "30"))
    session_refresh_threshold_minutes: int = int(os.getenv("SESSION_REFRESH_THRESHOLD_MINUTES", "5"))
    database_url: str = os.getenv("DATABASE_URL", "")
    bootstrap_database_url: str = os.getenv("BOOTSTRAP_DATABASE_URL", "")
    database_admin_url: str = os.getenv("DATABASE_ADMIN_URL", "")
    bootstrap_tenant_key: str = os.getenv("BOOTSTRAP_TENANT_KEY", "")
    super_bootstrap_secret: str = os.getenv("SUPER_BOOTSTRAP_SECRET", "")
    super_mfa_encryption_key: str = os.getenv("SUPER_MFA_ENCRYPTION_KEY", "")
    brevo_api_key: str = os.getenv("BREVO_API_KEY", "")
    email_from: str = os.getenv("EMAIL_FROM", "")
    email_from_name: str = os.getenv("EMAIL_FROM_NAME", "UsersAPI")
    email_key: str = os.getenv("EMAIL_KEY", "")
    frontend_url: str = os.getenv("FRONTEND_URL", "")
    backend_url: str = os.getenv("BACKEND_URL", "")
    api_email_url: str = os.getenv("API_EMAIL_URL", "")
    otp_api_key: str = os.getenv("OTP_API_KEY", "")
    otp_length: int = int(os.getenv("OTP_LENGTH", "6"))
    otp_expire_minutes: int = int(os.getenv("OTP_EXPIRE_MINUTES", "10"))
    otp_max_attempts: int = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
    whatsapp_token: str = os.getenv("WHATSAPP_TOKEN", "")
    whatsapp_phone_id: str = os.getenv("WHATSAPP_PHONE_ID", "")
    whatsapp_mode: str = os.getenv("WHATSAPP_MODE", "template")
    whatsapp_api_url: str = os.getenv("WHATSAPP_API_URL", "")


settings = Settings()
