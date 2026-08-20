import os

import requests

from ..logging_config import logger


# ============================================================
# CONFIGURACIÓN
# ============================================================

ACCESS_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
WHATSAPP_MODE = os.getenv(
    "WHATSAPP_MODE",
    "template",
)


# ============================================================
# FORMATEAR NÚMERO
# ============================================================

def format_number(number: str) -> str:
    """
    Normaliza números de Colombia.

    Ejemplos:

        3246865765
        +573246865765
        573246865765

    Todos terminan como:

        573246865765
    """

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
    """
    Envía un mensaje mediante WhatsApp Cloud API.

    IMPORTANTE:

    - Si WhatsApp responde 2xx -> retorna la respuesta JSON.
    - Si WhatsApp responde error -> retorna None.
    - Nunca lanza una excepción por un error HTTP de WhatsApp.

    Esto permite que la creación/actualización del usuario
    NO falle solamente porque WhatsApp esté caído o tenga
    un problema de autenticación.
    """

    # ========================================================
    # VALIDAR TOKEN
    # ========================================================

    if not ACCESS_TOKEN:

        logger.error(
            "WHATSAPP_TOKEN no está configurado"
        )

        return None

    # ========================================================
    # VALIDAR PHONE ID
    # ========================================================

    if not WHATSAPP_PHONE_ID:

        logger.error(
            "WHATSAPP_PHONE_ID no está configurado"
        )

        return None

    # ========================================================
    # VALIDAR DESTINATARIO
    # ========================================================

    if not to_number:

        logger.error(
            "No se puede enviar WhatsApp: "
            "el número de teléfono está vacío"
        )

        return None

    normalized_number = format_number(
        to_number
    )

    # ========================================================
    # URL GRAPH API
    # ========================================================

    url = (
        "https://graph.facebook.com/v25.0/"
        f"{WHATSAPP_PHONE_ID}/messages"
    )

    # ========================================================
    # HEADERS
    # ========================================================

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    # ========================================================
    # MENSAJE DE TEXTO
    # ========================================================

    if WHATSAPP_MODE.lower() == "text":

        if not message:

            logger.error(
                "WHATSAPP_MODE=text pero no se recibió "
                "ningún mensaje"
            )

            return None

        data = {
            "messaging_product": "whatsapp",
            "to": normalized_number,
            "type": "text",
            "text": {
                "body": message,
            },
        }

    # ========================================================
    # PLANTILLA
    # ========================================================

    else:

        template = {
            "name": template_name,
            "language": {
                "code": "en_US",
            },
        }

        # ----------------------------------------------------
        # PARÁMETROS DE LA PLANTILLA
        # ----------------------------------------------------

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

    # ========================================================
    # LOG PAYLOAD
    # ========================================================

    logger.debug(
        "Payload enviado a WhatsApp: %s",
        data,
    )

    # ========================================================
    # PETICIÓN
    # ========================================================

    try:

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=30,
        )

        # ====================================================
        # ÉXITO
        # ====================================================

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
                "status=%s | "
                "to=%s | "
                "mode=%s | "
                "template=%s",
                response.status_code,
                normalized_number,
                WHATSAPP_MODE,
                template_name,
            )

            logger.debug(
                "Respuesta WhatsApp: %s",
                response_data,
            )

            return response_data

        # ====================================================
        # ERROR HTTP
        # ====================================================

        logger.error(
            "Error HTTP WhatsApp | "
            "status=%s | "
            "response=%s | "
            "to=%s | "
            "mode=%s | "
            "template=%s",
            response.status_code,
            response.text,
            normalized_number,
            WHATSAPP_MODE,
            template_name,
        )

        return None

    # ========================================================
    # ERROR DE CONEXIÓN
    # ========================================================

    except requests.exceptions.RequestException as exc:

        logger.error(
            "Error de conexión WhatsApp | "
            "to=%s | "
            "mode=%s | "
            "template=%s | "
            "error=%s",
            normalized_number,
            WHATSAPP_MODE,
            template_name,
            str(exc),
        )

        return None

    # ========================================================
    # ERROR INESPERADO
    # ========================================================

    except Exception:

        logger.exception(
            "Error inesperado WhatsApp | "
            "to=%s | "
            "mode=%s | "
            "template=%s",
            normalized_number,
            WHATSAPP_MODE,
            template_name,
        )

        return None