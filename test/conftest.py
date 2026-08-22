import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from UsersAPI.database import engine, get_db
from UsersAPI.main import app


@pytest.fixture
def db_session():
    """Sesión aislada por prueba; nunca persiste datos en la BD configurada."""
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection)

    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session):
    """Cliente HTTP usando la misma transacción de db_session."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
