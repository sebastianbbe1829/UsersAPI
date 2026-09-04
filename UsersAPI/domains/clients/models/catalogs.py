from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class IdentificationTypeDB(Base):
    __tablename__ = "identification_types"
    __table_args__ = (
        UniqueConstraint("code", name="uq_identification_types_code"),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    code = Column(String(30), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    person_type = Column(String(20), nullable=False)
    active = Column(Boolean, nullable=False, server_default=text("true"))

    clients = relationship("ClientDB", back_populates="identification_type")


class CountryDB(Base):
    __tablename__ = "countries"
    __table_args__ = (
        UniqueConstraint("code", name="uq_countries_code"),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    # code/name remain the physical compatibility fields: Alpha-2 / short name.
    code = Column(String(2), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    short_name_lower = Column(String(100), nullable=True)
    full_name = Column(String(200), nullable=True)
    alpha3_code = Column(String(3), nullable=True, unique=True, index=True)
    numeric_code = Column(Integer, nullable=True, unique=True, index=True)
    remarks = Column(String(500), nullable=True)
    independent = Column(Boolean, nullable=True)
    territory_name = Column(String(250), nullable=True)
    status = Column(String(50), nullable=True)
    active = Column(Boolean, nullable=False, server_default=text("true"))

    departments = relationship("DepartmentDB", back_populates="country")
    clients = relationship("ClientDB", back_populates="country")


class DepartmentDB(Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("country_id", "code", name="uq_departments_country_code"),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    country_id = Column(
        Integer,
        ForeignKey("users_api.countries.id"),
        nullable=False,
        index=True,
    )
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    active = Column(Boolean, nullable=False, server_default=text("true"))

    country = relationship("CountryDB", back_populates="departments")
    cities = relationship("CityDB", back_populates="department")
    clients = relationship("ClientDB", back_populates="department")


class CityDB(Base):
    __tablename__ = "cities"
    __table_args__ = (
        UniqueConstraint("department_id", "code", name="uq_cities_department_code"),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    department_id = Column(
        Integer,
        ForeignKey("users_api.departments.id"),
        nullable=False,
        index=True,
    )
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(
        String(50), nullable=False, server_default=text("'Municipio'")
    )
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    active = Column(Boolean, nullable=False, server_default=text("true"))

    department = relationship("DepartmentDB", back_populates="cities")
    clients = relationship("ClientDB", back_populates="city")
