import os

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
import resend

from ..logging_config import logger


load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")


# Build absolute paths from project root
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# Configure Jinja2
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def send_email(
    recipient: str,
    subject: str,
    message: str,
    dni: str,
    token: str
):
    """
    Send an email using Resend with HTML rendered from a Jinja2 template.

    :param recipient: Email address of the receiver
    :param subject: Subject line of the email
    :param message: Main body text of the message
    :param dni: DNI of the user
    :param token: Activation token for the user
    """

    logger.info(
        f"Preparing to send email to {recipient} "
        f"with subject '{subject}'"
    )

    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY is not configured")
        raise RuntimeError("RESEND_API_KEY is not configured")

    if not EMAIL_FROM:
        logger.error("EMAIL_FROM is not configured")
        raise RuntimeError("EMAIL_FROM is not configured")

    # Configure Resend
    resend.api_key = RESEND_API_KEY

    # Render HTML template
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

    # Send email through Resend
    try:
        params = {
            "from": EMAIL_FROM,
            "to": [recipient],
            "subject": subject,
            "html": html_content,
        }

        response = resend.Emails.send(params)

        logger.info(
            f"Email sent to {recipient} with subject '{subject}' "
            f"via Resend"
        )

        logger.debug(
            f"Resend email id: {response}"
        )

        return response

    except Exception:
        logger.exception("Error sending email through Resend")
        raise