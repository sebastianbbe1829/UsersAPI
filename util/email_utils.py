import os
import smtplib
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from jinja2 import Environment, FileSystemLoader
from ..logging_config import logger

# Load environment variables
load_dotenv()
EMAIL_USER = os.getenv("EMAIL_USER", "correo@malo.com")
EMAIL_PASS = os.getenv("EMAIL_PASS", "contraseñamala")


# Build absolute path to templates folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# Configure Jinja2
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

def send_email(recipient: str, subject: str, message: str):
    """
    Send an email with HTML rendered from a template and inline logo.
    :param recipient: Email address of the receiver
    :param subject: Subject line of the email
    :param message: Main body text of the message
    """
    logger.info(f"Preparing to send email to {recipient} with subject '{subject}'")
    logger.info(f"Email details: {EMAIL_USER}, {EMAIL_PASS}")
    
    if not EMAIL_USER or not EMAIL_PASS:
        logger.error("Environment variables EMAIL_USER/EMAIL_PASS not configured")
        raise RuntimeError("Email environment variables not configured")

    # Render HTML template
    try:
        template = env.get_template("email_base.html")
        html_content = template.render(
            sender=EMAIL_USER,
            recipient=recipient,
            subject=subject,
            message=message
        )
    except Exception:
        logger.exception("Error loading or rendering HTML template")
        raise

    # Build MIME message (related to allow inline images)
    msg = MIMEMultipart("related")
    msg["From"] = EMAIL_USER
    msg["To"] = recipient
    msg["Subject"] = subject

    alternative = MIMEMultipart("alternative")
    msg.attach(alternative)
    alternative.attach(MIMEText(html_content, "html", "utf-8"))

    # Attach logo inline
    try:
        LOGO_PATH = os.path.join(BASE_DIR, "static", "logo.png")
        
        with open(LOGO_PATH, "rb") as f:
            logo = MIMEImage(f.read())
            logo.add_header("Content-ID", "<logo>")
            logo.add_header("Content-Disposition", "inline", filename="logo.png")
            msg.attach(logo)
    except Exception:
        logger.exception("Error attaching logo image")

    # Send email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
            logger.info(f"Email sent to {recipient} with subject '{subject}'")
    except Exception:
        logger.exception("Error sending email")
        raise
