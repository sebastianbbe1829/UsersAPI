from fastapi import Depends
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import GlobalUserDB, UserTenantDB
from ..schemas import LoginRequest, SuperLoginRequest
from ..settings import settings

from ..services.auth_context_service import get_current_user_from_token
from ..services.auth_audit_service import close_login_session, create_login_session
from ..services.auth_service import (
    create_access_token as create_access_token_service,
    login_user as login_user_service,
    oauth2_scheme,
    verify_password as verify_password_service,
)
from ..services.global_auth_service import (
    get_current_super_user,
    login_super_user as login_super_user_service,