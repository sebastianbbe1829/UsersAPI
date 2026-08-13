import os
import requests
from ..logging_config import logger

ACCESS_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_ID")
WHATSAPP_MODE = os.getenv("WHATSAPP_MODE", "template")  # valores: "template" o "text"

def format_number(number: str) -> str:
    number = number.strip()
    if number.startswith("+"):
        return number.replace("+", "")
    elif number.startswith("57"):
        return number
    else:
        return f"57{number}"

def send_whatsapp(to_number: str, message: str, template_name: str = "hello_world"):
    """
    Envía un mensaje de WhatsApp. Según WHATSAPP_MODE:
    - "template": usa el template indicado (por defecto hello_world).
    - "text": envía mensaje libre.
    """
    normalized_number = format_number(to_number)

    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    if WHATSAPP_MODE == "text":
        # Producción: mensaje libre
        data = {
            "messaging_product": "whatsapp",
            "to": normalized_number,
            "type": "text",
            "text": {"body": message}
        }
    else:
        # Prueba: template (ej. hello_world, bienvenida, actualizar, eliminar)
        data = {
            "messaging_product": "whatsapp",
            "to": normalized_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en_US"}
            }
        }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        logger.info(
            f"WhatsApp enviado | to={normalized_number} | mode={WHATSAPP_MODE} | template={template_name}"
        )
        return response.json()
    except Exception as e:
        logger.error(
            f"Error al enviar WhatsApp | to={normalized_number} | mode={WHATSAPP_MODE} | template={template_name} | error={str(e)}"
        )
        return None
