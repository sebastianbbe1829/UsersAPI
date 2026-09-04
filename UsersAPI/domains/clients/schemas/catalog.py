from pydantic import BaseModel, ConfigDict


class IdentificationTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    person_type: str


class CountryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    country_id: int
    code: str
    name: str


class CityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    code: str
    name: str
