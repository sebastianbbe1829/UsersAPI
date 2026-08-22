import requests

from ..logging_config import logger
from ..settings import settings


# ============================================================
# CONFIGURACIÓN
# ============================================================

ACCESS_TOKEN = settings.whatsapp_token
WHATSAPP_PHONE_ID = settings.whatsapp_phone_id
WHATSAPP_MODE = settings.whatsapp_mode


# ============================================================
# FORMATEAR NÚMERO
# ============================================================

def format_number(number: str) -> str:
    """Normaliza números de Colombia."""

    number = str(number).strip()

    if number.startswith("+"):
        return number[1:]

    if number.startswith("57"):
        return number

    return f"57{number}"


# ============================================================
# ENVIAR WHATSAPP
# ============================================================

def send_whatsapp(
    to_number: str,
    message: str | None = None,
    template_name: str = "hello_world",
    parameters: list | None = None,
):
    """Envía un mensaje mediante WhatsApp Cloud API."""

    if not ACCESS_TOKEN:
        logger.error("WHATSAPP_TOKEN no está configurado")
        return None

    if not WHATSAPP_PHONE_ID:
        logger.error("WHATSAPP_PHONE_ID no está configurado")
        return None

    if not to_number:
        logger.error(
            "No se puede enviar WhatsApp: el número de teléfono está vacío"
        )
        return None

    normalized_number = format_number(to_number)

    url = (
        "https://graph.facebook.com/v25.0/"
        f"{WHATSAPP_PHONE_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    if WHATSAPP_MODE.lower() == "text":
        if not message:
            logger.error(
                "WHATSAPP_MODE=text pero no se recibió ningún mensaje"
            )
            return None

        data = {
            "messaging_product": "whatsapp",
            "to": normalized_number,
            "type": "text",
            "text": {"body": message},
        }

    else:
        template = {
            "name": template_name,
            "language": {"code": "en_US"},
        }

        if parameters:
            template["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": str(parameter),
                        }
                        for parameter in parameters
                    ],
                }
            ]

        data = {
            "messaging_product": "whatsapp",
            "to": normalized_number,
            "type": "template",
            "template": template,
        }

    logger.debug(
        "Payload enviado a WhatsApp: %s",
        data,
    )

    try:
        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=30,
        )

        if response.ok:
            try:
                response_data = response.json()
            except ValueError:
                response_data = {
                    "status_code": response.status_code,
                    "text": response.text,
                }

            logger.info(
                "WhatsApp enviado correctamente | "
                "status=%s | to=%s | mode=%s | template=%s",
                response.status_code,
                normalized_number,
                WHATSAPP_MODE,
                template_name,
            )

            logger.debug("Respuesta WhatsApp: %s", response_data)
            return response_data

        logger.error(
            "Error HTTP WhatsApp | status=%s | response=%s | "
            "to=%s | mode=%s | template=%s",
            response.status_code,
            response.text,
            normalized_number,
            WHATSAPP_MODE,
            template_name,
        )

        return None

    except requests.exceptions.RequestException as exc:
        logger.error(
            "Error de conexión WhatsApp | to=%s | mode=%s | "
            "template=%s | error=%s",
            normalized_number,
            WHATSAPP_MODE,
            template_name,
            str(exc),
        )
        return None

    except Exception:
        logger.exception(
            "Error inesperado WhatsApp | to=%s | mode=%s | template=%s",
            normalized_number,
            WHATSAPP_MODE,
            template_name,
        )
        return None
