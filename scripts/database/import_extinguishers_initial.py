"""Carga inicial de extintores desde CSV.

Esta utilidad existe únicamente para la migración inicial de inventario.
No forma parte de la API ni del flujo normal de la aplicación.

Uso:
    python -m scripts.database.import_extinguishers_initial \
        --tenant-id 1 \
        --csv ruta/al/archivo.csv

Reglas de migración:
- El CSV usa ';' como separador.
- REVISION 1..4 con X determina la última revisión conocida.
- No se crean revisiones históricas que no estén en el CSV.
- La fecha de la revisión inicial se registra como CURRENT_DATE de PostgreSQL.
- La revisión importada no tiene inspector conocido.
- Los pares bueno/malo se convierten a GOOD/BAD/NA.
- Un mismo código de extintor no puede existir previamente en el tenant.
- La carga completa es transaccional: si una fila falla, no se importa ninguna.
"""

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

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
    "se registra fecha de migración. Información histórica no disponible."
)

TYPE_ALIASES = {
    "PQS": "POLVO_QUIMICO_SECO",
    "POLVO QUIMICO SECO": "POLVO_QUIMICO_SECO",
    "POLVO QUIMICO SECO PQS": "POLVO_QUIMICO_SECO",
    "DIOXIDO DE CARBONO": "CO2",
    "CO2": "CO2",
    "AGENTE LIMPIO": "AGENTE_LIMPIO",
}


class MigrationError(ValueError):
    """Error controlado de validación de una fila del CSV."""


def normalize_header(value: str) -> str:
    """Normaliza espacios y BOM sin cambiar el nombre funcional."""
    return re.sub(r"\s+", " ", value.strip().replace("\ufeff", ""))


def normalize_value(value: str | None) -> str:
    return "" if value is None else value.strip()


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
    value = normalize_value(value)
    if not value:
        return None

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

    raise MigrationError(
        f"Fila {row_number}: fecha inválida en '{field_name}': '{value}'. "
        "Formatos aceptados: DD/MM/YYYY, DD-MM-YYYY o YYYY-MM-DD."
    )


def get_revision_number(row: dict[str, str], row_number: int) -> int:
    marked = [
        number
        for number in range(1, 5)
        if is_marked(row.get(f"REVISION {number}"))
    ]

    if not marked:
        raise MigrationError(
            f"Fila {row_number}: no se encontró una X en REVISION 1..4."
        )

    if len(marked) > 1:
        raise MigrationError(
            f"Fila {row_number}: hay más de una revisión marcada: {marked}."
        )

    return marked[0]


def get_item_result(
    row: dict[str, str],
    good_column: str,
    bad_column: str,
    row_number: int,
) -> str:
    good = is_marked(row.get(good_column))
    bad = is_marked(row.get(bad_column))

    if good and bad:
        raise MigrationError(
            f"Fila {row_number}: '{good_column}' y '{bad_column}' no pueden estar marcados simultáneamente."
        )
    if good:
        return "GOOD"
    if bad:
        return "BAD"
    return "NA"


def get_overall_result(item_results: list[str]) -> str:
    """Deriva el estado sin considerar datos desconocidos como aptos."""
    if "BAD" in item_results:
        return "REQUIERE_MANTENIMIENTO"
    if all(result == "GOOD" for result in item_results):
        return "APTO"
    return "REQUIERE_MANTENIMIENTO"


def append_migration_observation(original: str | None) -> str:
    original = normalize_value(original)
    if original:
        return f"{original} {MIGRATION_OBSERVATION}"
    return MIGRATION_OBSERVATION


def validate_headers(headers: list[str]) -> None:
    normalized = [normalize_header(header) for header in headers]
    missing = sorted(REQUIRED_COLUMNS.difference(normalized))
    if missing:
        raise MigrationError(
            "Faltan columnas obligatorias en el CSV: " + ", ".join(missing)
        )


def resolve_type(
    type_by_code: dict[str, ExtinguisherTypeDB],
    type_by_name: dict[str, ExtinguisherTypeDB],
    value: str,
    row_number: int,
) -> ExtinguisherTypeDB:
    raw = normalize_value(value)
    if not raw:
        raise MigrationError(f"Fila {row_number}: TIPO EXTINTOR es obligatorio.")

    key = catalog_key(raw)
    code_key = catalog_key(TYPE_ALIASES.get(key, raw))
    item = type_by_code.get(code_key) or type_by_name.get(key)

    if item is None:
        raise MigrationError(
            f"Fila {row_number}: tipo de extintor no encontrado en el catálogo: '{value}'."
        )

    return item


def import_csv(csv_path: Path, tenant_id: int) -> tuple[int, int]:
    if tenant_id <= 0:
        raise MigrationError("tenant_id debe ser mayor que cero.")

    if not csv_path.is_file():
        raise MigrationError(f"No existe el archivo CSV: {csv_path}")

    db = SessionLocal()
    created_extinguishers = 0
    created_inspections = 0

    try:
        set_rls_tenant(db, tenant_id)

        with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file, delimiter=";")
            if reader.fieldnames is None:
                raise MigrationError("El CSV no tiene encabezados.")

            reader.fieldnames = [normalize_header(field) for field in reader.fieldnames]
            validate_headers(reader.fieldnames)

            # La fecha de migración proviene de PostgreSQL, equivalente a SYSDATE
            # para esta carga, y es la misma para todas las filas.
            migration_date = db.execute(text("SELECT CURRENT_DATE")).scalar_one()

            types = (
                db.query(ExtinguisherTypeDB)
                .filter(ExtinguisherTypeDB.active.is_(True))
                .all()
            )
            type_by_code = {catalog_key(item.code): item for item in types}
            type_by_name = {catalog_key(item.name): item for item in types}

            inspection_items = (
                db.query(ExtinguisherInspectionItemDB)
                .filter(ExtinguisherInspectionItemDB.active.is_(True))
                .order_by(
                    ExtinguisherInspectionItemDB.display_order,
                    ExtinguisherInspectionItemDB.id,
                )
                .all()
            )
            item_by_code = {item.code: item for item in inspection_items}

            missing_items = sorted(set(ITEM_COLUMNS) - set(item_by_code))
            if missing_items:
                raise MigrationError(
                    "El catálogo de ítems de inspección no contiene: "
                    + ", ".join(missing_items)
                )

            for row_number, raw_row in enumerate(reader, start=2):
                row = {
                    normalize_header(k): normalize_value(v)
                    for k, v in raw_row.items()
                    if k is not None
                }

                code = normalize_value(row.get("ID"))
                if not code:
                    raise MigrationError(f"Fila {row_number}: ID es obligatorio.")
                code = code.upper()

                existing = (
                    db.query(ExtinguisherDB)
                    .filter(
                        ExtinguisherDB.tenant_id == tenant_id,
                        ExtinguisherDB.code == code,
                    )
                    .first()
                )
                if existing is not None:
                    raise MigrationError(
                        f"Fila {row_number}: el extintor '{code}' ya existe en el tenant {tenant_id}."
                    )

                extinguisher_type = resolve_type(
                    type_by_code,
                    type_by_name,
                    row.get("TIPO EXTINTOR", ""),
                    row_number,
                )

                revision_number = get_revision_number(row, row_number)

                item_results = [
                    get_item_result(row, good_column, bad_column, row_number)
                    for good_column, bad_column in ITEM_COLUMNS.values()
                ]
                overall_result = get_overall_result(item_results)
                observations = append_migration_observation(row.get("OBSERVACIONES"))

                extinguisher = ExtinguisherDB(
                    tenant_id=tenant_id,
                    code=code,
                    extinguisher_type_id=extinguisher_type.id,
                    capacity=normalize_value(row.get("CAPACIDAD")) or None,
                    location=normalize_value(row.get("UBICACION")) or None,
                    last_recharge_date=parse_date(
                        row.get("Ultima recarga"), "Ultima recarga", row_number
                    ),
                    next_recharge_date=parse_date(
                        row.get("Proxima recarga"), "Proxima recarga", row_number
                    ),
                    last_hydrostatic_test_date=parse_date(
                        row.get("FECHA PRUEBA HIDROSTATICA Ultima"),
                        "FECHA PRUEBA HIDROSTATICA Ultima",
                        row_number,
                    ),
                    next_hydrostatic_test_date=parse_date(
                        row.get("FECHA PRUEBA HIDROSTATICA Proxima"),
                        "FECHA PRUEBA HIDROSTATICA Proxima",
                        row_number,
                    ),
                    inspections_since_hydrostatic_test=revision_number,
                    inspection_cycle=1,
                    status="ACTIVE",
                    is_stock=False,
                    active=True,
                )
                db.add(extinguisher)
                db.flush()

                inspection = ExtinguisherInspectionDB(
                    tenant_id=tenant_id,
                    extinguisher_id=extinguisher.id,
                    inspection_date=migration_date,
                    inspector_user_id=None,
                    inspection_number=revision_number,
                    inspection_cycle=1,
                    result=overall_result,
                    observations=observations,
                    hydrostatic_test_performed=False,
                    hydrostatic_test_date=None,
                    next_hydrostatic_test_date=None,
                )
                db.add(inspection)
                db.flush()

                for item_code, result in zip(ITEM_COLUMNS, item_results):
                    db.add(
                        ExtinguisherInspectionResultDB(
                            inspection_id=inspection.id,
                            inspection_item_id=item_by_code[item_code].id,
                            result=result,
                            observation=(
                                "Dato no disponible en la fuente de migración."
                                if result == "NA"
                                else None
                            ),
                        )
                    )

                created_extinguishers += 1
                created_inspections += 1

        db.commit()
        return created_extinguishers, created_inspections

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga inicial de extintores desde CSV")
    parser.add_argument("--tenant-id", type=int, required=True, help="ID del tenant destino")
    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Ruta al CSV separado por punto y coma",
    )
    args = parser.parse_args()

    try:
        extinguishers, inspections = import_csv(args.csv, args.tenant_id)
    except MigrationError as exc:
        raise SystemExit(f"ERROR DE MIGRACIÓN: {exc}") from exc
    except Exception as exc:
        raise SystemExit(f"ERROR DE BASE DE DATOS: {exc}") from exc

    print(f"Extintores creados: {extinguishers}")
    print(f"Revisiones iniciales creadas: {inspections}")
    print("Carga inicial completada correctamente.")


if __name__ == "__main__":
    main()
