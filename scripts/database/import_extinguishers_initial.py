"""Carga inicial de extintores desde CSV.

Esta utilidad existe únicamente para la migración inicial de inventario.
No forma parte de la API ni del flujo normal de la aplicación.

Uso:
    python -m scripts.database.import_extinguishers_initial \
        --tenant-id 1 \
        --csv ruta/al/archivo.csv \
        --dry-run

    python -m scripts.database.import_extinguishers_initial \
        --tenant-id 1 \
        --csv ruta/al/archivo.csv

Reglas de migración:
- El CSV usa ';' como separador.
- REVISION 1..4 con X determina la revisión conocida.
- Si ninguna revisión está marcada, se usa revisión 0 para identificarla como desconocida.
- La revisión 0 representa información histórica de revisión desconocida proveniente de migración inicial.
- La fecha de la inspección se registra como CURRENT_DATE de PostgreSQL.
- Las fechas históricas no interpretables se guardan como NULL y su texto original pasa a OBSERVACIONES.
- La revisión importada no tiene inspector conocido.
- Los pares bueno/malo se convierten a GOOD/BAD/NA.
- Un mismo código de extintor no puede existir previamente en el tenant.
- La carga completa es transaccional: si una fila falla, no se importa ninguna.
- Las fechas MM/YYYY se normalizan al primer día de ese mes.
- Las fechas month-YYYY con abreviatura de mes en español se normalizan al primer día de ese mes.
- Las fechas que contienen únicamente YYYY se normalizan al 01/01/YYYY.
- --dry-run valida sin insertar ni modificar datos.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import text

from UsersAPI.database import SessionLocal, set_rls_tenant
from UsersAPI.models import (
    ExtinguisherDB,
    ExtinguisherInspectionDB,
    ExtinguisherInspectionItemDB,
    ExtinguisherInspectionResultDB,
    ExtinguisherTypeDB,
)


REVISION_COLUMNS = tuple(f"REVISION {number}" for number in range(1, 5))

ITEM_COLUMNS = {
    "MANOMETER": ("Manómetro bueno", "Manómetro malo"),
    "HANDLE": ("Manija bueno", "Manija malo"),
    "PIN": ("Pasador bueno", "Pasador malo"),
    "LABEL": ("Etiqueta bueno", "Etiqueta malo"),
    "PAINT": ("Pintura bueno", "Pintura malo"),
    "CYLINDER": ("Cilindro bueno", "Cilindro malo"),
    "SIGNAGE": ("Señalizacion bueno", "Señalizacion malo"),
}

REQUIRED_COLUMNS = {
    "ID",
    "TIPO EXTINTOR",
    "CAPACIDAD",
    "UBICACION",
    "Ultima recarga",
    "Proxima recarga",
    "FECHA PRUEBA HIDROSTATICA Ultima",
    "FECHA PRUEBA HIDROSTATICA Proxima",
    "OBSERVACIONES",
    *REVISION_COLUMNS,
    *(column for pair in ITEM_COLUMNS.values() for column in pair),
}

MIGRATION_OBSERVATION = (
    "Carga inicial por migración. Fecha de la revisión original no disponible; "
    "se registra fecha de migración."
)

UNKNOWN_REVISION_OBSERVATION = (
    "Revisión histórica no identificada en la fuente original; se registra revisión 0."
)

TYPE_ALIASES = {
    "PQS": "POLVO_QUIMICO_SECO",
    "POLVO QUIMICO SECO": "POLVO_QUIMICO_SECO",
    "POLVO QUIMICO SECO PQS": "POLVO_QUIMICO_SECO",
    "MULTIPO": "POLVO_QUIMICO_SECO",
    "MULTIPRO": "POLVO_QUIMICO_SECO",
    "MULTIPROPOSITO": "POLVO_QUIMICO_SECO",
    "MULTIPROPOSITO PQS": "POLVO_QUIMICO_SECO",
    "DIOXIDO DE CARBONO": "CO2",
    "CO2": "CO2",
    "H2O": "AGUA",
    "AGUA": "AGUA",
    "AGENTE LIMPIO": "AGENTE_LIMPIO",
    "TIPO K": "TIPO_K",
}


class MigrationError(ValueError):
    """Error controlado de validación de una fila del CSV."""


def normalize_header(value: str) -> str:
    """Normaliza espacios y BOM sin cambiar el nombre funcional."""
    return re.sub(r"\s+", " ", value.strip().replace("\ufeff", ""))


def normalize_value(value: str | None) -> str:
    return "" if value is None else value.strip()


def read_csv_text(csv_path: Path) -> str:
    """Lee CSVs UTF-8, UTF-8 con BOM o Windows-1252."""
    raw = csv_path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise MigrationError(
        f"No se pudo determinar una codificación compatible para el CSV: {csv_path}"
    )


def catalog_key(value: str | None) -> str:
    """Normaliza nombres/códigos para comparar datos humanos del CSV."""
    value = normalize_value(value).upper()
    value = unicodedata.normalize("NFD", value)
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def is_marked(value: str | None) -> bool:
    """Acepta las marcas habituales del Excel/CSV."""
    normalized = normalize_value(value).upper()
    return normalized in {"X", "✓", "SI", "SÍ", "TRUE", "1"}


def parse_date(value: str | None, field_name: str, row_number: int) -> date | None:
    """Convierte fechas estructuradas del CSV al primer día del mes/año."""
    value = normalize_value(value)
    if not value:
        return None

    month_year_match = re.fullmatch(r"(\d{1,2})[/-](\d{4})", value)
    if month_year_match:
        month = int(month_year_match.group(1))
        year = int(month_year_match.group(2))
        try:
            return date(year, month, 1)
        except ValueError:
            return None

    spanish_months = {
        "ENE": 1,
        "FEB": 2,
        "MAR": 3,
        "ABR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "AGO": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DIC": 12,
    }
    spanish_month_year_match = re.fullmatch(r"([A-Za-zÁÉÍÓÚáéíóúÑñ]{3,})[/-](\d{2}|\d{4})", value)
    if spanish_month_year_match:
        month_text = catalog_key(spanish_month_year_match.group(1)).replace(" ", "")
        month = spanish_months.get(month_text[:3])
        year_text = spanish_month_year_match.group(2)
        if month is not None:
            year = int(year_text)
            if len(year_text) == 2:
                year += 2000
            try:
                return date(year, month, 1)
            except ValueError:
                return None

    if re.fullmatch(r"\d{4}", value):
        return date(int(value), 1, 1)

    formats = (
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d-%m-%y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
