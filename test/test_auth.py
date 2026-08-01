import sys
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from UsersAPI.controllers.auth_controller import create_access_token, pwd_context, verify_password
from UsersAPI.database import SessionLocal
from UsersAPI.main import app
from UsersAPI.models.user import UserDB


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_password_verification_in_memory():
    plain = "123456"
    hash_value = pwd_context.hash(plain)

    assert verify_password(plain, hash_value) is True
    assert verify_password("otrovalor", hash_value) is False


def test_password_update_is_stored_once_and_can_be_verified(db_session: Session):
    dni = f"{uuid4().int % 100000000:08d}"
    email = f"{uuid4().hex[:8]}@example.com"

    user = UserDB(
        dni=dni,
        name="Test User",
        email=email,
        status=True,
        phone="1111111",
        password=pwd_context.hash("oldpass"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token({"sub": user.dni})
    client = TestClient(app)
    response = client.patch(
        f"/users/{user.dni}",
        json={"password": "newpass"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    db_session.expire_all()
    updated_user = db_session.query(UserDB).filter(UserDB.dni == user.dni).first()
    assert updated_user is not None
    assert verify_password("newpass", updated_user.password) is True
    assert verify_password("oldpass", updated_user.password) is False

    db_session.delete(updated_user)
    db_session.commit()


def test_invalid_user_payload_returns_validation_error(db_session: Session):
    dni = f"{uuid4().int % 100000000:08d}"
    email = f"{uuid4().hex[:8]}@example.com"

    user = UserDB(
        dni=dni,
        name="Test User",
        email=email,
        status=True,
        phone="1111111",
        password=pwd_context.hash("oldpass"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token({"sub": user.dni})
    client = TestClient(app)
    response = client.post(
        "/users",
        json={"dni": user.dni, "name": "Test"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body

    db_session.delete(user)
    db_session.commit()


def test_expired_token_returns_expired_message(db_session: Session):
    dni = f"{uuid4().int % 100000000:08d}"
    email = f"{uuid4().hex[:8]}@example.com"

    user = UserDB(
        dni=dni,
        name="Test User",
        email=email,
        status=True,
        phone="1111111",
        password=pwd_context.hash("oldpass"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token({"sub": user.dni}, expires_delta=timedelta(minutes=-5))
    client = TestClient(app)
    response = client.get(
        "/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Token expirado"

    db_session.delete(user)
    db_session.commit()
