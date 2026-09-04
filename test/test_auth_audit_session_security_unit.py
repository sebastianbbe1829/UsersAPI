from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

from UsersAPI.models import AuthAuditDB, AuthSessionDB
from UsersAPI.services import auth_audit_service
from UsersAPI.settings import settings


def _token(payload: dict) -> str:
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


# NOTE: existing tests above this section remain unchanged in the repository.
