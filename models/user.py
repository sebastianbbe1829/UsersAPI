from sqlalchemy import Column, Date, DateTime, Integer, String, Boolean, text
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
    created_at = Column(DateTime, nullable=False)
    created_by = Column(String(100), nullable=False)
    created_by_bd = Column(
        String(100),
        nullable=True,
        server_default=text("USER")  # aquí respetas el default de Oracle
    )
