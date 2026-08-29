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