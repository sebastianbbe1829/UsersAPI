import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from UsersAPI.database import SessionLocal
from UsersAPI.models.user import UserDB
from UsersAPI.controllers.auth_controller import get_password_hash


def create_initial_user():
    db = SessionLocal()
    try:
        existing = db.query(UserDB).filter(UserDB.email == "admin@example.com").first()
        if existing:
            print("El usuario inicial ya existe")
            return

        user = UserDB(
            dni="00000001",
            name="Admin",
            email="admin@example.com",
            status=True,
            phone="3000000000",
            password=get_password_hash("admin123"),
        )
        db.add(user)
        db.commit()
        print("Usuario inicial creado: admin@example.com / admin123")
    finally:
        db.close()


if __name__ == "__main__":
    create_initial_user()
