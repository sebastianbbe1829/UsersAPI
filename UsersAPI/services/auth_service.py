import math

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..database import get_db
from ..logging_config import logger
from ..models import UserDB
from ..settings import settings

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as exc:
        logger.error("Error al verificar password: %s", exc)
        return False


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str, db: Session) -> UserDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        dni: str = payload.get("sub") # pyright: ignore[reportAssignmentType]
        if dni is None:
            raise credentials_exception
    except ExpiredSignatureError as exc:
        logger.warning("Token expirado: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except JWTError as exc:
        logger.warning("Token inválido: %s", exc)
        raise credentials_exception from exc

    # Validar que el usuario exista y esté activo
    user = db.query(UserDB).filter(UserDB.dni == dni, UserDB.status == 1).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o inactivo")
    return user


def login_user(form_data: OAuth2PasswordRequestForm, db: Session):
    logger.debug("Variables de entorno para autenticación: %s, %s, %s", SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES)
    logger.info("Intento de login con username=%s", form_data.username)
    user = db.query(UserDB).filter(UserDB.email == form_data.username,
                                    UserDB.status == 1
                                   ).first()
    if not user:
        logger.warning("Usuario %s no encontrado en BD", form_data.username)
        raise HTTPException(status_code=400, detail="Credenciales inválidas o usuario inactivo")

    if not verify_password(form_data.password, user.password): # pyright: ignore[reportArgumentType]
        logger.warning("Password inválido para usuario %s", form_data.username)
        raise HTTPException(status_code=400, detail="Credenciales inválidas")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.dni}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


def validate_token(token: str, db: Session):
    try:
        logger.debug("Variables de entorno para autenticación: %s, %s, %s", SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        logger.debug("Payload decodificado: %s", payload)
        exp = payload.get("exp")
        user_dni: str = payload.get("sub") # pyright: ignore[reportAssignmentType]
        if user_dni is None:
            logger.error("❌ Token inválido: no contiene 'sub'")
            raise HTTPException(status_code=401, detail="Token inválido")

        user = db.query(UserDB).filter(UserDB.dni == user_dni, UserDB.status == 1).first()
        if not user:
            logger.warning("Usuario con dni=%s no encontrado en BD", user_dni)
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        now = int(datetime.now(timezone.utc).timestamp())
        logger.debug("Tiempo actual=%s, expiración=%s", now, exp)
        if exp is not None and exp < now:
            logger.warning("⏰ Token expirado para usuario dni=%s, email=%s", user_dni, user.email)
            raise HTTPException(status_code=401, detail="Token expirado")

        # Calcular tiempo restante
        remaining_seconds = exp - now if exp else None
        remaining_minutes_exact = (remaining_seconds / 60) if remaining_seconds else None
        remaining_minutes_rounded = math.ceil(remaining_minutes_exact) if remaining_minutes_exact else None
        logger.info("✅ Token válido para usuario dni=%s, email=%s", user_dni, user.email)
        return {
            "valid": True,
            "expiration": exp,
            "now": now,
            "remaining_seconds": remaining_seconds,
            "remaining_minutes_exact": remaining_minutes_exact,
            "remaining_minutes_rounded": remaining_minutes_rounded,
            "user": {
                "dni": user.dni,
                "email": user.email
            }
        }
    except JWTError as exc:
        logger.error("❌ Error al decodificar token: %s", exc)
        raise HTTPException(status_code=401, detail="Token inválido") from exc
