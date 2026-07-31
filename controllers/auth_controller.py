import time
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from ..logging_config import logger
from ..database import get_db
from ..models import UserDB
from dotenv import load_dotenv
import os

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY no está definido en variables de entorno")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))

# SECRET_KEY="4pr3nd13nd0"
# ALGORITHM="HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES=15



pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error al verificar password: {e}")
        return False

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        dni: str = payload.get("sub")
        if dni is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(UserDB).filter(UserDB.dni == dni).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

def login_user(form_data: OAuth2PasswordRequestForm, db: Session):
    logger.debug(f"Variables de entorno para autenticación: {SECRET_KEY}, {ALGORITHM}, {ACCESS_TOKEN_EXPIRE_MINUTES}")
    logger.info(f"Intento de login con username={form_data.username}")
    user = db.query(UserDB).filter(UserDB.email == form_data.username).first()
    if not user:
        logger.warning(f"Usuario {form_data.username} no encontrado en BD")
        raise HTTPException(status_code=400, detail="Credenciales inválidas")

    if not verify_password(form_data.password, user.password):
        logger.warning(f"Password inválido para usuario {form_data.username}")
        raise HTTPException(status_code=400, detail="Credenciales inválidas")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.dni}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

def validate_token(token: str, db: Session):
    try:
        logger.debug(f"Variables de entorno para autenticación: {SECRET_KEY}, {ALGORITHM}, {ACCESS_TOKEN_EXPIRE_MINUTES}")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        logger.debug(f"Payload decodificado: {payload}")
        exp = payload.get("exp")
        user_dni: str = payload.get("sub")
        if user_dni is None:
            logger.error("❌ Token inválido: no contiene 'sub'")
            raise HTTPException(status_code=401, detail="Token inválido")

        user = db.query(UserDB).filter(UserDB.dni == user_dni).first()
        if not user:
            logger.warning(f"Usuario con dni={user_dni} no encontrado en BD")
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        now = int(time.time())
        logger.debug(f"Tiempo actual={now}, expiración={exp}")
        if exp is not None and exp < now:
            logger.warning(f"⏰ Token expirado para usuario dni={user_dni}")
            raise HTTPException(status_code=401, detail="Token expirado")

        logger.info(f"✅ Token válido para usuario dni={user_dni}")
        return {"valid": True, "expiration": exp, "now": now, "user": {"dni": user.dni, "email": user.email}}
    except JWTError:
        logger.error(f"❌ Error al decodificar token: {e}")
        raise HTTPException(status_code=401, detail="Token inválido")
