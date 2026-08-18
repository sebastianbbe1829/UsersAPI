import os

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
import requests

from ..logging_config import logger


load_dotenv()


MAILERSEND_API_KEY = os.getenv("MAILERSEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
FRONTEND_URL = os.getenv("FRONTEND_URL")
BACKEND_URL = os.getenv("BACKEND_URL")


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR)
)


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

    if not MAILERSEND_API_KEY:
        logger.error("MAILERSEND_API_KEY is not configured")
        raise RuntimeError(
            "MAILERSEND_API_KEY is not configured"
        )

    if not EMAIL_FROM:
        logger.error("EMAIL_FROM is not configured")
        raise RuntimeError(
            "EMAIL_FROM is not configured"
        )

    if not FRONTEND_URL:
        logger.error("FRONTEND_URL is not configured")
        raise RuntimeError(
            "FRONTEND_URL is not configured"
        )

    if not BACKEND_URL:
        logger.error("BACKEND_URL is not configured")
        raise RuntimeError(
            "BACKEND_URL is not configured"
        )

    # -----------------------------------------
    # URL DE ACTIVACIÓN
    # -----------------------------------------

    activation_url = (
        f"{FRONTEND_URL.rstrip('/')}"
        f"/users/activate/{dni}/{token}"
    )

    # -----------------------------------------
    # URL DEL LOGO
    # -----------------------------------------

    logo_url = (
        f"{BACKEND_URL.rstrip('/')}"
        f"/static/logo.png"
    )

    logger.info(
        f"Activation URL: {activation_url}"
    )

    logger.info(
        f"Logo URL: {logo_url}"
    )

    # -----------------------------------------
    # RENDER HTML
    # -----------------------------------------

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

    except Exception:

        logger.exception(
            "Error loading or rendering HTML email template"
        )

        raise

    # -----------------------------------------
    # MAILERSEND
    # -----------------------------------------

    try:

        response = requests.post(
            "https://api.mailersend.com/v1/email",

            headers={
                "Authorization": (
                    f"Bearer {MAILERSEND_API_KEY}"
                ),
                "Content-Type": "application/json",
                "Accept": "application/json"
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

        if response.status_code != 202:

            logger.error(
                f"MailerSend error "
                f"{response.status_code}: "
                f"{response.text}"
            )

            response.raise_for_status()

        message_id = response.headers.get(
            "x-message-id"
        )

        logger.info(
            f"Email sent successfully to {recipient} "
            f"via MailerSend | "
            f"message_id={message_id}"
        )

        return {
            "status": "sent",
            "message_id": message_id
        }

    except Exception:

        logger.exception(
            "Error sending email through MailerSend"
        )

        raise