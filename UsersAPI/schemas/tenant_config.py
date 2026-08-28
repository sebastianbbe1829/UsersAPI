from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TenantConfigUpdate(BaseModel):

    app_title: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
        description="Título mostrado en la aplicación",
    )

    logo_url: str | None = Field(
        default=None,
        max_length=500,
        description="URL o ruta del logo del tenant",
    )

    primary_color: str | None = Field(
        default=None,
        description="Color principal en formato hexadecimal",
    )

    secondary_color: str | None = Field(
        default=None,
        description="Color secundario en formato hexadecimal",
    )

    @field_validator("primary_color", "secondary_color")
    @classmethod
    def validate_hex_color(cls, value: str | None) -> str | None:
        if value is None:
            return value

        if not value.startswith("#") or len(value) != 7:
            raise ValueError(
                "El color debe estar en formato hexadecimal #RRGGBB."
            )

        try:
            int(value[1:], 16)
        except ValueError as exc:
            raise ValueError(
                "El color debe estar en formato hexadecimal #RRGGBB."
            ) from exc

        return value.upper()


class TenantConfigRead(BaseModel):

    tenant_id: int
    name: str
    slug: str
    app_title: str
    logo_url: str | None
    primary_color: str
    secondary_color: str
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
