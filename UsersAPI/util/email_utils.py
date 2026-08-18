import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

from ..logging_config import logger


load_dotenv()


# ============================================================
# CONFIGURACIÓN SMTP MAILERSEND
# ============================================================

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.mailersend.net")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")


# ============================================================
# TEMPLATES
# ============================================================

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


# ============================================================
# ENVÍO DE CORREO
# ============================================================

def send_email(
    recipient: str,
    subject: str,
    message: str,
    dni: str,
    token: str
):
    """
    Envía un correo utilizando SMTP de MailerSend
    y el template HTML email_base.html.

    :param recipient: Email del destinatario
    :param subject: Asunto del correo
    :param message: Mensaje principal
    :param dni: DNI del usuario
    :param token: Token de activación
    """

    logger.info(
        f"Preparing to send email to {recipient} "
        f"with subject '{subject}'"
    )

    # ========================================================
    # VALIDACIONES
    # ========================================================

    if not SMTP_USERNAME:
        logger.error("SMTP_USERNAME is not configured")
        raise RuntimeError("SMTP_USERNAME is not configured")

    if not SMTP_PASSWORD:
        logger.error("SMTP_PASSWORD is not configured")
        raise RuntimeError("SMTP_PASSWORD is not configured")

    if not EMAIL_FROM:
        logger.error("EMAIL_FROM is not configured")
        raise RuntimeError("EMAIL_FROM is not configured")

    # ========================================================
    # RENDERIZAR TEMPLATE HTML
    # ========================================================

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

    # ========================================================
    # CREAR MENSAJE
    # ========================================================

    try:

        msg = MIMEMultipart("alternative")

        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = recipient

        # Versión texto
        text_content = message

        # Versión HTML
        msg.attach(
            MIMEText(text_content, "plain", "utf-8")
        )

        msg.attach(
            MIMEText(html_content, "html", "utf-8")
        )

    except Exception:

        logger.exception(
            "Error creating email message"
        )

        raise

    # ========================================================
    # ENVIAR MEDIANTE MAILERSEND SMTP
    # ========================================================

    try:

        logger.info(
            f"Connecting to SMTP server "
            f"{SMTP_SERVER}:{SMTP_PORT}"
        )

        with smtplib.SMTP(
            SMTP_SERVER,
            SMTP_PORT,
            timeout=30
        ) as server:

            # TLS
            server.starttls()

            # Autenticación
            server.login(
                SMTP_USERNAME,
                SMTP_PASSWORD
            )

            # Envío
            server.sendmail(
                EMAIL_FROM,
                recipient,
                msg.as_string()
            )

        logger.info(
            f"Email sent to {recipient} "
            f"with subject '{subject}' "
            f"via MailerSend SMTP"
        )

        return True

    except Exception:

        logger.exception(
            "Error sending email through MailerSend SMTP"
        )

        raise