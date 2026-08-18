import os

import requests
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

from ..logging_config import logger


load_dotenv()


MAILERSEND_API_KEY = os.getenv("MAILERSEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "UsersAPI")


# Build absolute paths from project root
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")


# Configure Jinja2
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
    """
    Send an email using MailerSend API
    with HTML rendered from a Jinja2 template.
    """

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

    # -------------------------------------------------
    # Render HTML template
    # -------------------------------------------------

    try:

        template = env.get_template("email_base.html")

        html_content = template.render(
            sender=EMAIL_FROM,
            recipient=recipient,
            subject=subject,
            message=message,
            dni=dni,
            token=token
        )

    except Exception:
        logger.exception(
            "Error loading or rendering HTML email template"
        )
        raise

    # -------------------------------------------------
    # Send through MailerSend API
    # -------------------------------------------------

    try:

        payload = {
            "from": {
                "email": EMAIL_FROM,
                "name": EMAIL_FROM_NAME
            },
            "to": [
                {
                    "email": recipient
                }
            ],
            "subject": subject,
            "html": html_content
        }

        headers = {
            "Authorization": f"Bearer {MAILERSEND_API_KEY}",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest"
        }

        response = requests.post(
            "https://api.mailersend.com/v1/email",
            headers=headers,
            json=payload,
            timeout=30
        )

        # MailerSend returns 202 when the email
        # has been accepted for processing.
        if response.status_code != 202:

            logger.error(
                f"MailerSend error "
                f"{response.status_code}: {response.text}"
            )

            response.raise_for_status()

        message_id = response.headers.get(
            "x-message-id"
        )

        logger.info(
            f"Email accepted by MailerSend | "
            f"to={recipient} | "
            f"message_id={message_id}"
        )

        return {
            "status": "accepted",
            "message_id": message_id
        }

    except requests.RequestException:
        logger.exception(
            "Error sending email through MailerSend API"
        )
        raise