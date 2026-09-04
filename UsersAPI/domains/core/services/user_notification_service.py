from ..logging_config import logger
from ..util.email_utils import send_email
from ..util.whatsapp_utils import send_whatsapp


def send_user_notifications(
    user,
    user_tenant,
    tenant_name: str,
    tenant_slug: str,
    es_reactivacion: bool,
):
    if es_reactivacion:
        email_template = "reactivation"
        email_subject = f"Tu cuenta en {tenant_name} fue reactivada"
        email_message = (
            f"Hola {user.name}, "
            f"tu cuenta en {tenant_name} ha sido reactivada exitosamente. "
            "Para completar el proceso, utiliza el botón para reactivar tu cuenta."
        )
    else:
        email_template = "activation"
        email_subject = f"Activa tu cuenta en {tenant_name}"
        email_message = (
            f"Hola {user.name}, "
            f"tu cuenta en {tenant_name} ha sido creada exitosamente."
        )

    try:
        send_email(
            recipient=user_tenant.email,
            subject=email_subject,
            message=email_message,
            dni=user.dni,
            token=user_tenant.activation_token,
            tenant_name=tenant_name,
            tenant_slug=tenant_slug,
            template=email_template,
        )
        logger.info(
            "Correo de usuario enviado",
            extra={
                "dni": user.dni,
                "email": user_tenant.email,
                "tenant_id": user_tenant.tenant_id,
                "template": email_template,
            },
        )
    except Exception as exc:
        logger.warning(
            "Usuario creado/reactivado pero falló el envío de correo: %s",
            exc,
        )

    try:
        if user_tenant.phone:
            whatsapp_response = send_whatsapp(
                to_number=user_tenant.phone,
                message=None,
                template_name="hello_world",
                parameters=None,
            )
            if whatsapp_response is not None:
                logger.info(
                    "WhatsApp de bienvenida enviado correctamente",
                    extra={
                        "dni": user.dni,
                        "phone": user_tenant.phone,
                        "tenant_id": user_tenant.tenant_id,
                    },
                )
    except Exception:
        logger.exception(
            "Error inesperado enviando WhatsApp",
            extra={
                "dni": user.dni,
                "phone": user_tenant.phone,
                "tenant_id": user_tenant.tenant_id,
            },
        )
