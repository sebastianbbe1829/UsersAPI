import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from UsersAPI.controllers.auth_controller import create_access_token, pwd_context
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


@pytest.fixture
def client():
    return TestClient(app)


def test_create_user_returns_201_and_persists_user(db_session: Session, client: TestClient):
    creator_dni = f"{uuid4().int % 100000000:08d}"
    creator_email = f"{uuid4().hex[:8]}@example.com"
    creator = UserDB(
        dni=creator_dni,
        name="Creator",
        email=creator_email,
        status=True,
        phone="3000000000",
        password=pwd_context.hash("segura123"),
    )
    db_session.add(creator)
    db_session.commit()
    db_session.refresh(creator)

    token = create_access_token({"sub": creator.dni})

    new_dni = f"{uuid4().int % 100000000:08d}"
    new_email = f"{uuid4().hex[:8]}@example.com"
    response = client.post(
        "/users",
        json={
            "dni": new_dni,
            "name": "Nuevo Usuario",
            "email": new_email,
            "phone": "3000000000",
            "password": "segura123",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["dni"] == new_dni
    assert payload["email"] == new_email

    stored = db_session.query(UserDB).filter(UserDB.dni == new_dni).first()
    assert stored is not None
    assert stored.email == new_email

    db_session.delete(stored)
    db_session.delete(creator)
    db_session.commit()


def test_delete_user_returns_safe_response(db_session: Session, client: TestClient):
    user_dni = f"{uuid4().int % 100000000:08d}"
    user_email = f"{uuid4().hex[:8]}@example.com"
    user = UserDB(
        dni=user_dni,
        name="Usuario Borrar",
        email=user_email,
        status=True,
        phone="3000000000",
        password=pwd_context.hash("segura123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token({"sub": user.dni})
    response = client.delete(
        f"/users/{user_dni}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Usuario eliminado correctamente"
    assert payload["dni"] == user_dni
    assert payload["email"] == user_email
    assert payload["name"] == "Usuario Borrar"
    assert payload["status"] is True
    assert payload["phone"] == "3000000000"
    assert "password" not in payload
    assert "id" not in payload

    assert db_session.query(UserDB).filter(UserDB.dni == user_dni).first() is None


def test_get_user_list_requires_authentication(client: TestClient):
    response = client.get("/users")
    assert response.status_code == 401
