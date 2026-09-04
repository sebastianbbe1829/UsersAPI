from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class IdentificationTypeBase(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=100)
    person_type: str = Field(pattern="^(NATURAL|JURIDICA)$")
    active: bool = True


class IdentificationTypeCreate(IdentificationTypeBase):
    pass


class IdentificationTypeUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    person_type: str | None = Field(default=None, pattern="^(NATURAL|JURIDICA)$")
    active: bool | None = None


class IdentificationTypeRead(IdentificationTypeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class CountryBase(BaseModel):
    code: str = Field(min_length=2, max_length=2)
    name: str = Field(min_length=1, max_length=100)
    short_name_lower: str | None = Field(default=None, max_length=100)
    full_name: str | None = Field(default=None, max_length=200)
    alpha3_code: str | None = Field(default=None, min_length=3, max_length=3)
    numeric_code: int | None = Field(default=None, ge=1, le=999)
    remarks: str | None = Field(default=None, max_length=500)
    independent: bool | None = None
    territory_name: str | None = Field(default=None, max_length=250)
    status: str | None = Field(default=None, max_length=50)
    active: bool = True


class CountryCreate(CountryBase):
    pass


class CountryUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=2)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    short_name_lower: str | None = Field(default=None, max_length=100)
    full_name: str | None = Field(default=None, max_length=200)
    alpha3_code: str | None = Field(default=None, min_length=3, max_length=3)
    numeric_code: int | None = Field(default=None, ge=1, le=999)
    remarks: str | None = Field(default=None, max_length=500)
    independent: bool | None = None
    territory_name: str | None = Field(default=None, max_length=250)
    status: str | None = Field(default=None, max_length=50)
    active: bool | None = None


class CountryRead(CountryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class DepartmentBase(BaseModel):
    country_id: int
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    active: bool = True


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    country_id: int | None = None
    code: str | None = Field(default=None, min_length=1, max_length=20)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    active: bool | None = None


class DepartmentRead(DepartmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class CityBase(BaseModel):
    department_id: int
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    type: str = Field(default="Municipio", min_length=1, max_length=50)
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    active: bool = True


class CityCreate(CityBase):
    pass


class CityUpdate(BaseModel):
    department_id: int | None = None
    code: str | None = Field(default=None, min_length=1, max_length=20)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: str | None = Field(default=None, min_length=1, max_length=50)
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    active: bool | None = None


class CityRead(CityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
