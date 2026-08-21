import os

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
import requests

from ..logging_config import logger


# ============================================================
# VARIABLES DE ENTORNO
# ============================================================

load_dotenv()

MAILERSEND_API_KEY = os.getenv("MAILERSEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")

FRONTEND_URL = os.getenv("FRONTEND_URL")
BACKEND_URL = os.getenv("BACKEND_URL")


# ============================================================
# CONFIGURACIÓN DE TEMPLATES
# ============================================================

# Estructura esperada:
#
# repo/
# └── UsersAPI/
#     ├── static/
#     │   └── logo.png
#     ├── templates/
#     │   └── email_base.html
#     └── UsersAPI/
#         └── util/
#             └── email_utils.py
#
# Desde email_utils.py subimos:
#
# util       -> UsersAPI
# UsersAPI   -> UsersAPI
# UsersAPI   -> repo
#
# Por eso usamos tres dirname.

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


# ============================================================
# JINJA2
# ============================================================

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
    """
    Envía un correo electrónico utilizando MailerSend.

    El contenido HTML se genera mediante Jinja2.

    Variables utilizadas:

    FRONTEND_URL
        URL pública del frontend.

    BACKEND_URL
        URL pública del backend.

    EMAIL_FROM
        Dirección autorizada por MailerSend.

    MAILERSEND_API_KEY
        API Key de MailerSend.

    Parámetros:

    recipient:
        Correo del destinatario.

    subject:
        Asunto del correo.

    message:
        Mensaje principal.

    dni:
        DNI del usuario.

    token:
        Token de activación.
    """

    logger.info(
        f"Preparing to send email to {recipient} "
        f"with subject '{subject}'"
    )


    # ========================================================
    # VALIDAR CONFIGURACIÓN
    # ========================================================

    if not MAILERSEND_API_KEY:

        logger.error(
            "MAILERSEND_API_KEY is not configured"
        )

        raise RuntimeError(
            "MAILERSEND_API_KEY is not configured"
        )


    if not EMAIL_FROM:

        logger.error(
            "EMAIL_FROM is not configured"
        )

        raise RuntimeError(
            "EMAIL_FROM is not configured"
        )


    if not FRONTEND_URL:

        logger.error(
            "FRONTEND_URL is not configured"
        )

        raise RuntimeError(
            "FRONTEND_URL is not configured"
        )


    if not BACKEND_URL:

        logger.error(
            "BACKEND_URL is not configured"
        )

        raise RuntimeError(
            "BACKEND_URL is not configured"
        )


    # ========================================================
    # NORMALIZAR URLS
    # ========================================================
    frontend_url = FRONTEND_URL.rstrip("/")
    backend_url = BACKEND_URL.rstrip("/")


    # ========================================================
    # URL DE ACTIVACIÓN
    # ========================================================
    activation_url = (
        f"{frontend_url}"
        f"/{tenant_slug}"
        f"/users/activate/{dni}/{token}"
        )


    # ========================================================
    # URL DEL LOGO
    # ========================================================

    logo_url = (
        f"{backend_url}"
        f"/static/logo.png"
    )


    logger.info(
        f"Activation URL: {activation_url}"
    )

    logger.info(
        f"Logo URL: {logo_url}"
    )


    # ========================================================
    # VALIDAR TEMPLATE
    # ========================================================

    template_path = os.path.join(
        TEMPLATE_DIR,
        "email_base.html"
    )


    if not os.path.isfile(template_path):

        logger.error(
            f"Email template not found: {template_path}"
        )

        raise RuntimeError(
            f"Email template not found: {template_path}"
        )


    # ========================================================
    # RENDERIZAR HTML
    # ========================================================

    try:

        template = env.get_template(
            "email_base.html"
        )


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


        logger.debug(
            "Email HTML template rendered successfully"
        )


    except Exception:

        logger.exception(
            "Error loading or rendering HTML email template"
        )

        raise


    # ========================================================
    # ENVIAR CON MAILERSEND
    # ========================================================

    try:

        response = requests.post(

            "https://api.mailersend.com/v1/email",

            headers={

                "Authorization": (
                    f"Bearer {MAILERSEND_API_KEY}"
                ),

                "Content-Type": (
                    "application/json"
                ),

                "Accept": (
                    "application/json"
                )

            },

            json={

                "from": {

                    "email": EMAIL_FROM,

                    "name": "UsersAPI"

                },

                "to": [

                    {

                        "email": recipient

                    }

                ],

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


        # ====================================================
        # MAILERSEND DEBE RESPONDER 202
        # ====================================================

        if response.status_code != 202:

            logger.error(

                f"MailerSend error "
                f"{response.status_code}: "
                f"{response.text}"

            )

            response.raise_for_status()


        # ====================================================
        # MESSAGE ID
        # ====================================================

        message_id = response.headers.get(
            "x-message-id"
        )


        logger.info(

            f"Email sent successfully to {recipient} "
            f"via MailerSend | "
            f"message_id={message_id}"

        )


        # ====================================================
        # RESPUESTA
        # ====================================================

        return {

            "status": "sent",

            "message_id": message_id

        }


    except requests.exceptions.Timeout:

        logger.exception(
            "Timeout sending email through MailerSend"
        )

        raise RuntimeError(
            "Timeout connecting to MailerSend"
        )


    except requests.exceptions.RequestException:

        logger.exception(
            "HTTP error sending email through MailerSend"
        )

        raise


    except Exception:

        logger.exception(
            "Error sending email through MailerSend"
        )

        raise