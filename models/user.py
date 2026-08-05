from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy import Identity
from ..database import Base

class UserDB(Base):
    __tablename__ = "app_users"
    id = Column(
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )
    dni = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(100), index=True)
    email = Column(String(255), unique=True, index=True)
    status = Column(Boolean, default=True)
    phone = Column(String(20), nullable=True)
    password = Column(String(200), nullable=False)
