from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class ClientBase(BaseModel):
    identification_type_id: int
    identification_number: str = Field(min_length=1, max_length=50)
    person_type: str = Field(pattern="^(NATURAL|JURIDICA)$")
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    second_last_name: str | None = Field(default=None, max_length=100)
    business_name: str | None = Field(default=None, max_length=250)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=250)
    country_id: int | None = None
    department_id: int | None = None
    city_id: int | None = None
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|INACTIVE)$")
    consent_given: bool = False
    consent_at: datetime | None = None
    consent_source: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_person_identity(self):
        if self.person_type == "NATURAL":
            if not self.first_name or not self.last_name:
                raise ValueError("Natural person requires first_name and last_name")
        elif not self.business_name:
            raise ValueError("Legal person requires business_name")
        return self


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    identification_type_id: int | None = None
    identification_number: str | None = Field(default=None, min_length=1, max_length=50)
    person_type: str | None = Field(default=None, pattern="^(NATURAL|JURIDICA)$")
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    second_last_name: str | None = Field(default=None, max_length=100)
    business_name: str | None = Field(default=None, max_length=250)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=250)
    country_id: int | None = None
    department_id: int | None = None
    city_id: int | None = None
    status: str | None = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")
    consent_given: bool | None = None
    consent_at: datetime | None = None
    consent_source: str | None = Field(default=None, max_length=100)


class ClientRead(ClientBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: int
    full_name: str
    compliance_status: str
    is_listed: bool
    list_type: str | None
    created_at: datetime
    created_by: str
    updated_at: datetime | None
    updated_by: str | None
