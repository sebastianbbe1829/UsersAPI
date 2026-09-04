from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TenantConfigUpdate(BaseModel):
    app_title: str | None = Field(default=None, min_length=2, max_length=150)
    logo_url: str | None = Field(default=None, max_length=500)
    primary_color: str | None = Field(default=None)
    secondary_color: str | None = Field(default=None)

    @field_validator("primary_color", "secondary_color")
    @classmethod
    def validate_hex_color(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.startswith("#") or len(value) != 7:
            raise ValueError("El color debe estar en formato hexadecimal #RRGGBB.")
        try:
            int(value[1:], 16)
        except ValueError as exc:
            raise ValueError("El color debe estar en formato hexadecimal #RRGGBB.") from exc
        return value.upper()


class TenantConfigSuperUpdate(TenantConfigUpdate):
    max_login_attempts: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Máximo de intentos fallidos antes de bloquear. "
            "0 o vacío deshabilita el bloqueo."
        ),
    )


class TenantConfigRead(BaseModel):
    tenant_id: int
    name: str
    slug: str
    app_title: str
    logo_url: str | None
    primary_color: str
    secondary_color: str
    max_login_attempts: int | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
