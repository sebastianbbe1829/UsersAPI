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


def test_get_user_list_requires_authentication(client: TestClient):
    response = client.get("/users")
    assert response.status_code == 401
