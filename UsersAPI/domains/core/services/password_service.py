from argon2 import PasswordHasher

from ..logging_config import logger


# PasswordHasher de argon2-cffi reemplaza Passlib.
# Mantiene Argon2 como algoritmo de almacenamiento y verificación
# sin depender del módulo crypt eliminado de Python 3.13.
pwd_context = PasswordHasher()


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    try:
        return pwd_context.verify(
            hashed_password,
            plain_password,
        )
    except Exception as exc:
        logger.error(
            "Error validando password: %s",
            exc,
        )
        return False


def get_password_hash(
    password: str,
) -> str:
    return pwd_context.hash(password)
