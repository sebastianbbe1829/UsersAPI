import os

from jinja2 import Environment, FileSystemLoader
import requests

from ..logging_config import logger
from ..settings import settings


# ============================================================
# CONFIGURACIÓN
# ============================================================

MAILERSEND_API_KEY = settings.mailersend_api_key
EMAIL_FROM = settings.email_from
FRONTEND_URL = settings.frontend_url
BACKEND_URL = settings.backend_url


# ============================================================
# CONFIGURACIÓN DE TEMPLATES
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

TEMPLATE_DIR = os.path.join(
    BASE_DIR,
    "templates"
)

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR)
)


# ============================================================
# SEND EMAIL
# ============================================================

def send_email(
    recipient: str,
    subject: str,
    message: str,
    dni: str,
    token: str,
    tenant_slug: str,
):
    """Envía un correo electrónico utilizando MailerSend."""

    logger.info(
        f"Preparing to send email to {recipient} "
        f"with subject '{subject}'"
    )

    if not MAILERSEND_API_KEY:
        logger.error("MAILERSEND_API_KEY is not configured")
        raise RuntimeError("MAILERSEND_API_KEY is not configured")

    if not EMAIL_FROM:
        logger.error("EMAIL_FROM is not configured")
        raise RuntimeError("EMAIL_FROM is not configured")

    if not FRONTEND_URL:
        logger.error("FRONTEND_URL is not configured")
        raise RuntimeError("FRONTEND_URL is not configured")

    if not BACKEND_URL:
        logger.error("BACKEND_URL is not configured")
        raise RuntimeError("BACKEND_URL is not configured")

    frontend_url = FRONTEND_URL.rstrip("/")
    backend_url = BACKEND_URL.rstrip("/")

    activation_url = (
        f"{frontend_url}"
        f"/{tenant_slug}"
        f"/users/activate/{dni}/{token}"
    )

    logo_url = f"{backend_url}/static/logo.png"

    logger.info(f"Activation URL: {activation_url}")
    logger.info(f"Logo URL: {logo_url}")

    template_path = os.path.join(
        TEMPLATE_DIR,
        "email_base.html"
    )

    if not os.path.isfile(template_path):
        logger.error(f"Email template not found: {template_path}")
        raise RuntimeError(f"Email template not found: {template_path}")

    try:
        template = env.get_template("email_base.html")

        html_content = template.render(
            sender=EMAIL_FROM,
            recipient=recipient,
            subject=subject,
            message=message,
            dni=dni,
            token=token,
            activation_url=activation_url,
            logo_url=logo_url
        )

        logger.debug("Email HTML template rendered successfully")

    except Exception:
        logger.exception("Error loading or rendering HTML email template")
        raise

    try:
        response = requests.post(
            "https://api.mailersend.com/v1/email",
            headers={
                "Authorization": f"Bearer {MAILERSEND_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={
                "from": {
                    "email": EMAIL_FROM,
                    "name": "UsersAPI"
                },
                "to": [{"email": recipient}],
                "subject": subject,
                "html": html_content,
                "text": (
                    f"{message}\n\n"
                    f"Activar cuenta:\n"
                    f"{activation_url}"
                )
            },
            timeout=30
        )

        if response.status_code != 202:
            logger.error(
                f"MailerSend error {response.status_code}: {response.text}"
            )
            response.raise_for_status()

        message_id = response.headers.get("x-message-id")

        logger.info(
            f"Email sent successfully to {recipient} via MailerSend | "
            f"message_id={message_id}"
        )

        return {
            "status": "sent",
            "message_id": message_id
        }

    except requests.exceptions.Timeout:
        logger.exception("Timeout sending email through MailerSend")
        raise RuntimeError("Timeout connecting to MailerSend")

    except requests.exceptions.RequestException:
        logger.exception("HTTP error sending email through MailerSend")
        raise

    except Exception:
        logger.exception("Error sending email through MailerSend")
        raise
