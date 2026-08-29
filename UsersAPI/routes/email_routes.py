import secrets

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from ..settings import settings
from ..util.email_utils import send_test_email


class EmailTestRequest(BaseModel):
    recipient: str = Field(..., min_length=3, max_length=320)
    subject: str = Field(
        default="Prueba de correo - UsersAPI",
        min_length=1,
        max_length=200,
    )
    message: str = Field(
        default="Este es un correo de prueba enviado desde UsersAPI utilizando Brevo.",
        min_length=1,
        max_length=5000,
    )


email_routes = APIRouter(
    prefix="/email",
    tags=["Email"],
)


@email_routes.post(
    "/test",
    status_code=status.HTTP_200_OK,
)
def test_email(
    datos: EmailTestRequest,
    x_email_test_key: str = Header(..., alias="X-Email-Test-Key"),
):
    """Envía un correo de prueba sin crear usuarios ni modificar la BD.

    El endpoint está protegido con una clave exclusiva para pruebas de email.
    """

    if not settings.email_test_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="EMAIL_TEST_KEY no está configurada.",
        )

    if not secrets.compare_digest(
        x_email_test_key,
        settings.email_test_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clave de prueba de email inválida.",
        )

    try:
        result = send_test_email(
            recipient=datos.recipient,
            subject=datos.subject,
            message=datos.message,
        )

        return {
            "status": "sent",
            "message": "Correo de prueba enviado correctamente.",
            "recipient": datos.recipient,
            "message_id": result.get("message_id"),
        }

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No fue posible enviar el correo de prueba.",
        )
