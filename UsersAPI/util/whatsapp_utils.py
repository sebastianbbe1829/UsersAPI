import os
import requests

from ..logging_config import logger


ACCESS_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
WHATSAPP_MODE = os.getenv("WHATSAPP_MODE", "template")


def format_number(number: str) -> str:
    number = str(number).strip()

    if number.startswith("+"):
        return number.replace("+", "")

    if number.startswith("57"):
        return number

    return f"57{number}"


def send_whatsapp(
    to_number: str,
    message: str,
    template_name: str = "hello_world",
    parameters: list = None,
):
    if not ACCESS_TOKEN:
        logger.error("WHATSAPP_TOKEN no está configurado")
        return None

    if not WHATSAPP_PHONE_ID:
        logger.error("WHATSAPP_PHONE_ID no está configurado")
        return None

    normalized_number = format_number(to_number)

    url = (
        f"https://graph.facebook.com/v25.0/"
        f"{WHATSAPP_PHONE_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    if WHATSAPP_MODE.lower() == "text":

        data = {
            "messaging_product": "whatsapp",
            "to": normalized_number,
            "type": "text",
            "text": {
                "body": message,
            },
        }

    else:

        template = {
            "name": template_name,
            "language": {
                "code": "en_US",
            },
        }

        # Solo enviar componentes cuando la plantilla
        # realmente tiene parámetros.
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
        f"Payload enviado a WhatsApp: {data}"
    )

    try:

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=30,
        )

        response.raise_for_status()

        response_data = response.json()

        logger.info(
            f"WhatsApp enviado correctamente | "
            f"to={normalized_number} | "
            f"mode={WHATSAPP_MODE} | "
            f"template={template_name}"
        )

        logger.debug(
            f"Respuesta WhatsApp: {response_data}"
        )

        return response_data

    except requests.exceptions.HTTPError:

        logger.error(
            f"Error HTTP WhatsApp | "
            f"status={response.status_code} | "
            f"response={response.text} | "
            f"to={normalized_number} | "
            f"mode={WHATSAPP_MODE} | "
            f"template={template_name}"
        )

        return None

    except requests.exceptions.RequestException as e:

        logger.error(
            f"Error de conexión WhatsApp | "
            f"to={normalized_number} | "
            f"mode={WHATSAPP_MODE} | "
            f"template={template_name} | "
            f"error={str(e)}"
        )

        return None

    except Exception:

        logger.exception(
            f"Error inesperado WhatsApp | "
            f"to={normalized_number} | "
            f"mode={WHATSAPP_MODE} | "
            f"template={template_name}"
        )

        return None