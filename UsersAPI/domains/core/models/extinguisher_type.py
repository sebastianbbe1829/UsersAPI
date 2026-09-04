from sqlalchemy import Boolean, Column, DateTime, Identity, Integer, String, text

from ..database import Base


class ExtinguisherTypeDB(Base):
    __tablename__ = "extinguisher_types"

    __table_args__ = {"schema": "users_api"}

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=True)
