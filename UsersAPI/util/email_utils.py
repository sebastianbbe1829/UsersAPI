import os

import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..logging_config import logger
from ..settings import settings


# ============================================================
# CONFIGURACIÓN
# ============================================================

BREVO_API_KEY = settings.brevo_api_key
EMAIL_FROM = settings.email_from
EMAIL_FROM_NAME = settings.email_from_name
FRONTEND_URL = settings.frontend_url
BACKEND_URL = settings.backend_url
API_EMAIL_URL = settings.api_email_url


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
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


# ============================================================
# SEND EMAIL
# ============================================================

def send_email(
    recipient: str,
    subject: str,
    message: str,
    dni: str | None = None,
    token: str | None = None,
    tenant_slug: str | None = None,
    tenant_name: str | None = None,
    template: str = "default",
):
    """Envía un correo transaccional utilizando Brevo.

    Templates soportados:
        - activation: activación de cuenta.
        - reactivation: reactivación de cuenta.
        - updated: actualización de usuario con acceso al login.
        - default: mensaje informativo sin botón.

    La comunicación se presenta siempre desde el tenant/empresa.
    """

    allowed_templates = {
        "activation",
        "reactivation",
        "updated",
        "default",
    }

    if template not in allowed_templates:
        raise ValueError(
            f"Email template inválido: {template}. "
            f"Valores permitidos: {', '.join(sorted(allowed_templates))}"
        )

    logger.info(
        f"Preparing to send email to {recipient} "
        f"with subject '{subject}' template='{template}'"
    )

    if not BREVO_API_KEY:
        logger.error("BREVO_API_KEY is not configured")
        raise RuntimeError("BREVO_API_KEY is not configured")

    if not EMAIL_FROM:
        logger.error("EMAIL_FROM is not configured")
        raise RuntimeError("EMAIL_FROM is not configured")

    if not BACKEND_URL:
        logger.error("BACKEND_URL is not configured")
        raise RuntimeError("BACKEND_URL is not configured")

    backend_url = BACKEND_URL.rstrip("/")
    logo_url = f"{backend_url}/static/logo.png"

    tenant_display_name = (
        tenant_name.strip()
        if tenant_name and tenant_name.strip()
        else tenant_slug
    )

    if "UsersAPI" in subject:
        if template == "activation":
            subject = f"Activa tu cuenta en {tenant_display_name}"
        elif template == "reactivation":
            subject = f"Reactiva tu cuenta en {tenant_display_name}"
        elif template == "updated":
            subject = f"Tu usuario en {tenant_display_name} fue actualizado"

    activation_url = None
    login_url = None

    if template in {"activation", "reactivation"}:
        if not FRONTEND_URL:
            logger.error("FRONTEND_URL is not configured")
            raise RuntimeError("FRONTEND_URL is not configured")

        if not tenant_slug:
            raise RuntimeError(
                "tenant_slug is required for activation emails"
            )

        if not dni:
            raise RuntimeError(
                "dni is required for activation emails"
            )

        if not token:
            raise RuntimeError(
                "token is required for activation emails"
            )

        frontend_url = FRONTEND_URL.rstrip("/")
        activation_url = (
            f"{frontend_url}"
            f"/{tenant_slug}"
            f"/users/activate/{dni}/{token}"
        )

        logger.info(f"Activation URL: {activation_url}")

    if template == "updated":
        if not FRONTEND_URL:
            logger.error("FRONTEND_URL is not configured")
            raise RuntimeError("FRONTEND_URL is not configured")

        if not tenant_slug:
            raise RuntimeError(
                "tenant_slug is required for updated emails"
            )

        frontend_url = FRONTEND_URL.rstrip("/")
        login_url = f"{frontend_url}/{tenant_slug}/login"

        logger.info(f"Login URL: {login_url}")

    template_path = os.path.join(
        TEMPLATE_DIR,
        "email_base.html"
    )

    if not os.path.isfile(template_path):
        logger.error(f"Email template not found: {template_path}")
        raise RuntimeError(f"Email template not found: {template_path}")

    try:
        email_template = env.get_template("email_base.html")

        html_content = email_template.render(
            sender=EMAIL_FROM,
            recipient=recipient,
            subject=subject,
            message=message,
            dni=dni,
            token=token,
            activation_url=activation_url,
            login_url=login_url,
            logo_url=logo_url,
            tenant_name=tenant_display_name,
            template=template,
        )

        logger.debug("Email HTML template rendered successfully")

    except Exception:
        logger.exception("Error loading or rendering HTML email template")
        raise

    if template == "activation":
        text_content = (
            f"{message}\n\n"
            f"Activar cuenta:\n"
            f"{activation_url}"
        )
    elif template == "reactivation":
        text_content = (
            f"{message}\n\n"
            f"Reactivar cuenta:\n"
            f"{activation_url}"
        )
    elif template == "updated":
        text_content = (
            f"{message}\n\n"
            f"Ingresar a la aplicación:\n"
            f"{login_url}"
        )
    else:
        text_content = message

    try:
        response = requests.post(
            API_EMAIL_URL,
            headers={
                "api-key": BREVO_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={
                "sender": {
                    "email": EMAIL_FROM,
                    "name": EMAIL_FROM_NAME
                },
                "to": [{"email": recipient}],
                "subject": subject,
                "htmlContent": html_content,
                "textContent": text_content,
            },
            timeout=30
        )

        if response.status_code != 201:
            logger.error(
                f"Brevo error {response.status_code}: {response.text}"
            )
            response.raise_for_status()

        response_data = response.json()
        message_id = response_data.get("messageId")

        logger.info(
            f"Email sent successfully to {recipient} via Brevo | "
            f"message_id={message_id} template={template}"
        )

        return {
            "status": "sent",
            "message_id": message_id
        }

    except requests.exceptions.Timeout:
        logger.exception("Timeout sending email through Brevo")
        raise RuntimeError("Timeout connecting to Brevo")

    except requests.exceptions.RequestException:
        logger.exception("HTTP error sending email through Brevo")
        raise

    except Exception:
        logger.exception("Error sending email through Brevo")
        raise


# ============================================================
# EMAIL DE PRUEBA
# ============================================================

def send_brevo_email(
    recipient: str,
    subject: str = "Prueba de correo",
    message: str = "Este es un correo de prueba enviado desde el sistema.",
):
    """Envía el template por defecto sin botón.

    No crea usuarios, tenants ni registros en la base de datos.
    """

    return send_email(
        recipient=recipient,
        subject=subject,
        message=message,
        template="default",
    )
