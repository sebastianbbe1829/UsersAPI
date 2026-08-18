import os
import base64

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
import requests

from ..logging_config import logger


load_dotenv()


# ============================================================
# CONFIGURACIÓN
# ============================================================

MAILERSEND_API_KEY = os.getenv("MAILERSEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
FRONTEND_URL = os.getenv("FRONTEND_URL")

MAILERSEND_URL = "https://api.mailersend.com/v1/email"


# ============================================================
# DIRECTORIOS
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

STATIC_DIR = os.path.join(
    BASE_DIR,
    "static"
)

LOGO_PATH = os.path.join(
    STATIC_DIR,
    "logo.png"
)


# ============================================================
# JINJA2
# ============================================================

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR)
)


# ============================================================
# ENVIAR EMAIL
# ============================================================

def send_email(
    recipient: str,
    subject: str,
    message: str,
    dni: str,
    token: str
):

    logger.info(
        f"Preparing to send email to {recipient} "
        f"with subject '{subject}'"
    )


    # --------------------------------------------------------
    # Validaciones
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # URL DE ACTIVACIÓN
    # --------------------------------------------------------

    activation_url = (
        f"{FRONTEND_URL.rstrip('/')}"
        f"/users/activate/"
        f"{dni}/"
        f"{token}"
    )


    logger.info(
        f"Activation URL generated: {activation_url}"
    )


    # --------------------------------------------------------
    # TEMPLATE
    # --------------------------------------------------------

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

            frontend_url=FRONTEND_URL

        )


    except Exception:

        logger.exception(
            "Error loading or rendering HTML email template"
        )

        raise


    # --------------------------------------------------------
    # LOGO
    # --------------------------------------------------------

    attachments = []


    if os.path.exists(LOGO_PATH):

        logger.info(
            f"Loading email logo from: {LOGO_PATH}"
        )


        try:

            with open(
                LOGO_PATH,
                "rb"
            ) as logo_file:

                logo_base64 = base64.b64encode(
                    logo_file.read()
                ).decode("utf-8")


            attachments.append({

                "filename": "logo.png",

                "content": logo_base64,

                "disposition": "inline",

                "id": "logo"

            })


        except Exception:

            logger.exception(
                "Error loading email logo"
            )

            raise

    else:

        logger.warning(
            f"Email logo not found: {LOGO_PATH}"
        )


    # --------------------------------------------------------
    # PAYLOAD MAILERSEND
    # --------------------------------------------------------

    payload = {

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
            f"Activa tu cuenta aquí:\n"
            f"{activation_url}"
        )

    }


    # --------------------------------------------------------
    # ATTACHMENT DEL LOGO
    # --------------------------------------------------------

    if attachments:

        payload["attachments"] = attachments


    # --------------------------------------------------------
    # HEADERS
    # --------------------------------------------------------

    headers = {

        "Authorization":
            f"Bearer {MAILERSEND_API_KEY}",

        "Content-Type":
            "application/json",

        "Accept":
            "application/json"

    }


    # --------------------------------------------------------
    # ENVIAR
    # --------------------------------------------------------

    try:

        response = requests.post(

            MAILERSEND_URL,

            json=payload,

            headers=headers,

            timeout=30

        )


        if response.status_code != 202:

            logger.error(

                "MailerSend returned unexpected status "
                f"{response.status_code}: "
                f"{response.text}"

            )

            response.raise_for_status()


        message_id = response.headers.get(
            "x-message-id"
        )


        logger.info(

            "Email accepted by MailerSend | "
            f"to={recipient} | "
            f"message_id={message_id}"

        )


        return {

            "status": "accepted",

            "message_id": message_id

        }


    except requests.RequestException:

        logger.exception(
            "Error sending email through MailerSend"
        )

        raise