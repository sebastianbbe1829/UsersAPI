from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import UserDB
from ..services.auth_service import (
    create_access_token as create_access_token_service,
    get_current_user as get_current_user_service,
    get_password_hash as get_password_hash_service,
    login_user as login_user_service,
    oauth2_scheme,
    pwd_context,
    validate_token as validate_token_service,
    verify_password as verify_password_service,
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return verify_password_service(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return get_password_hash_service(password)


def create_access_token(data: dict, expires_delta=None) -> str:
    return create_access_token_service(data, expires_delta)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserDB:
    return get_current_user_service(token, db)


def login_user(form_data: OAuth2PasswordRequestForm, db: Session):
    return login_user_service(form_data, db)


def validate_token(token: str, db: Session):
    return validate_token_service(token, db)
