import pytest
from fastapi.testclient import TestClient

from UsersAPI.database import SessionLocal, get_db
from UsersAPI.main import app


@pytest.fixture
def db_session():
    """Sesión compartida por la prueba y la aplicación.

    La aplicación usa exactamente esta sesión mediante dependency override.
    Al terminar cada prueba se hace rollback, por lo que pytest nunca deja
    datos persistidos en la base de datos configurada para las pruebas.
    """
    db = SessionLocal()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield db
    finally:
        db.rollback()
        app.dependency_overrides.pop(get_db, None)
        db.close()


@pytest.fixture
def client(db_session):
    """Cliente HTTP que utiliza la misma sesión transaccional de la prueba."""
    return TestClient(app)
