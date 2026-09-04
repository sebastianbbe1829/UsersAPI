from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class ClientCreate(BaseModel):
    client_type: str = Field(default="PERSON", max_length=20)
    id_type: str = Field(..., min_length=1, max_length=20)
    id_number: str = Field(..., min_length=1, max_length=30)
    first_name: str | None = Field(None, max_length=50)
    middle_name: str | None = Field(None, max_length=50)
    last_name: str | None = Field(None, max_length=50)
    second_last_name: str | None = Field(None, max_length=50)
    legal_name: str | None = Field(None, max_length=150)
    trade_name: str | None = Field(None, max_length=150)
    birth_date: date | None = None
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    country_code: str = Field(default="CO", min_length=2, max_length=3)
    department_code: str | None = Field(None, max_length=10)
    city_code: str | None = Field(None, max_length=10)
    address: str | None = Field(None, max_length=200)
    consent_contact: bool = False
    consent_contact_at: datetime | None = None

    @model_validator(mode="after")
    def validate_type_data(self):
        self.client_type = self.client_type.strip().upper()
        self.id_type = self.id_type.strip().upper()
        self.id_number = self.id_number.strip().upper()
        self.country_code = self.country_code.strip().upper()
        if self.client_type not in {"PERSON", "COMPANY"}:
            raise ValueError("client_type debe ser PERSON o COMPANY")
        if self.client_type == "PERSON" and (not self.first_name or not self.last_name):
            raise ValueError("PERSON requiere first_name y last_name")
        if self.client_type == "COMPANY" and not self.legal_name:
            raise ValueError("COMPANY requiere legal_name")
        if self.consent_contact and self.consent_contact_at is None:
            self.consent_contact_at = datetime.now()
        if not self.consent_contact:
            self.consent_contact_at = None
        return self


class ClientUpdate(BaseModel):
    client_type: str | None = Field(None, max_length=20)
    id_type: str | None = Field(None, min_length=1, max_length=20)
    id_number: str | None = Field(None, min_length=1, max_length=30)
    first_name: str | None = Field(None, max_length=50)
    middle_name: str | None = Field(None, max_length=50)
    last_name: str | None = Field(None, max_length=50)
    second_last_name: str | None = Field(None, max_length=50)
    legal_name: str | None = Field(None, max_length=150)
    trade_name: str | None = Field(None, max_length=150)
    birth_date: date | None = None
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    country_code: str | None = Field(None, min_length=2, max_length=3)
    department_code: str | None = Field(None, max_length=10)
    city_code: str | None = Field(None, max_length=10)
    address: str | None = Field(None, max_length=200)
    consent_contact: bool | None = None
    consent_contact_at: datetime | None = None
    status: str | None = Field(None, max_length=20)


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    tenant_id: int
    client_type: str
    id_type: str
    id_number: str
    first_name: str | None
    middle_name: str | None
    last_name: str | None
    second_last_name: str | None
    legal_name: str | None
    trade_name: str | None
    full_name: str | None
    birth_date: date | None
    phone: str | None
    email: EmailStr | None
    country_code: str
    department_code: str | None
    city_code: str | None
    address: str | None
    consent_contact: bool
    consent_contact_at: datetime | None
    status: str
    compliance_status: str
    is_listed: bool
    list_type: str | None
    last_screening_at: datetime | None
    created_by: str
    created_at: datetime
    updated_by: str | None
    updated_at: datetime | None


class ClientDeleteResponse(BaseModel):
    message: str
    uuid: UUID
