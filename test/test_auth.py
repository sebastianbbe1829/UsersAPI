import pytest
from sqlalchemy.orm import Session
from auth import verify_password, pwd_context
from database import get_db
from models.user import UserDB

def test_password_verification_in_memory():
    plain = "123456"
    hash_value = pwd_context.hash(plain)

    # Verificación en memoria
    assert verify_password(plain, hash_value) is True
    assert verify_password("otrovalor", hash_value) is False

def test_password_verification_db():
    db: Session = next(get_db())

    # Busca el usuario en la BD
    user = db.query(UserDB).filter(UserDB.email == "sebastianbbe@gmail.com").first()
    assert user is not None, "Usuario no encontrado en BD"

    plain = "123456"
    result = verify_password(plain, user.password)

    print(f"\nPlain: {plain}\nHash: {user.password}\nResultado: {result}")

    assert result is True
