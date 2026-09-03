from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExtinguisherInspectionItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    active: bool
    display_order: int
    created_at: datetime
    updated_at: datetime | None


class ExtinguisherInspectionResultCreate(BaseModel):
    inspection_item_id: int = Field(..., gt=0)
    result: str = Field(..., min_length=1, max_length=30)
    observation: str | None = None


class ExtinguisherInspectionResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    inspection_item_id: int
    result: str
    observation: str | None
    inspection_item: ExtinguisherInspectionItemRead


class ExtinguisherInspectionCreate(BaseModel):
    inspection_date: date
    result: str = Field(..., min_length=1, max_length=30)
    observations: str | None = None
    hydrostatic_test_performed: bool = False
    hydrostatic_test_date: date | None = None
    next_hydrostatic_test_date: date | None = None
    items: list[ExtinguisherInspectionResultCreate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_hydrostatic_dates(self):
        if self.hydrostatic_test_performed and self.hydrostatic_test_date is None:
            raise ValueError("La fecha de la prueba hidrostática es obligatoria")
        if self.hydrostatic_test_performed and self.next_hydrostatic_test_date is None:
            raise ValueError("La fecha de la próxima prueba hidrostática es obligatoria")
        if not self.hydrostatic_test_performed and self.hydrostatic_test_date is not None:
            raise ValueError("No se puede informar fecha de prueba hidrostática sin realizarla")
        if (
            not self.hydrostatic_test_performed
            and self.next_hydrostatic_test_date is not None
        ):
            raise ValueError(
                "No se puede informar próxima fecha de prueba hidrostática sin realizar la prueba"
            )
        if self.hydrostatic_test_date and self.hydrostatic_test_date > self.inspection_date:
            raise ValueError(
                "La fecha de la prueba hidrostática no puede ser posterior a la revisión"
            )
        if (
            self.hydrostatic_test_date
            and self.next_hydrostatic_test_date
            and self.next_hydrostatic_test_date <= self.hydrostatic_test_date
        ):
            raise ValueError(
                "La próxima prueba hidrostática debe ser posterior a la fecha de la prueba"
            )
        return self


class ExtinguisherInspectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    extinguisher_id: int
    inspection_date: date
    inspector_user_id: int | None
    inspection_number: int
    inspection_cycle: int
    result: str
    observations: str | None
    hydrostatic_test_performed: bool
    hydrostatic_test_date: date | None
    next_hydrostatic_test_date: date | None
    created_at: datetime
    results: list[ExtinguisherInspectionResultRead]
