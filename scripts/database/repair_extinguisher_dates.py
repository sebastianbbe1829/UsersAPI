"""Repara las fechas de extintores ya cargados desde el CSV de migración.

El CSV original contiene fechas de recarga como ``jun-23`` y ``sep-22``.
El importador inicial no interpretaba abreviaturas de meses en español, por lo
que esas fechas quedaron NULL en la base de datos. Este script permite reparar
los 133 registros ya importados sin volver a crear extintores ni inspecciones.

Uso:
    python -m scripts.database.repair_extinguisher_dates \
        --tenant-id 1 \
        --csv data/extintores.csv

El proceso es transaccional y actualiza únicamente fechas que puedan
interpretarse correctamente. Las fechas no interpretables permanecen NULL.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
from datetime import date, datetime
from pathlib import Path

from UsersAPI.database import SessionLocal, set_rls_tenant
from UsersAPI.models import ExtinguisherDB


MONTHS_ES = {
    "ENE": 1,
    "ENERO": 1,
    "FEB": 2,
    "FEBRERO": 2,
    "MAR": 3,
    "MARZO": 3,
    "ABR": 4,
    "ABRIL": 4,
    "MAY": 5,
    "MAYO": 5,
    "JUN": 6,
    "JUNIO": 6,
    "JUL": 7,
    "JULIO": 7,
    "AGO": 8,
    "AGOSTO": 8,
    "SEP": 9,
    "SEPT": 9,
    "SEPTIEMBRE": 9,
    "OCT": 10,
    "OCTUBRE": 10,
    "NOV": 11,
    "NOVIEMBRE": 11,
    "DIC": 12,
    "DICIEMBRE": 12,
}

DATE_FIELDS = {
    "last_recharge_date": "Ultima recarga",
    "next_recharge_date": "Proxima recarga",
    "last_hydrostatic_test_date": "FECHA PRUEBA HIDROSTATICA Ultima",
    "next_hydrostatic_test_date": "FECHA PRUEBA HIDROSTATICA Proxima",
}


def normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().replace("\ufeff", ""))


def normalize_value(value: str | None) -> str:
    return "" if value is None else value.strip()


def read_csv_text(csv_path: Path) -> str:
    raw = csv_path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"No se pudo leer el CSV: {csv_path}")


def parse_date(value: str | None) -> date | None:
    value = normalize_value(value)
    if not value:
        return None

    # Excel suele exportar estas fechas como "jun-23", "sep-22", etc.
    month_year_match = re.fullmatch(r"([A-Za-zÁÉÍÓÚáéíóúÑñ]+)[ -](\d{2}|\d{4})", value)
    if month_year_match:
        month_text = month_year_match.group(1).upper()
        month = MONTHS_ES.get(month_text)
        if month is not None:
            year = int(month_year_match.group(2))
            if year < 100:
                year += 2000
            try:
                return date(year, month, 1)
            except ValueError:
                return None

    numeric_month_year = re.fullmatch(r"(\d{1,2})[/-](\d{2}|\d{4})", value)
    if numeric_month_year:
        month = int(numeric_month_year.group(1))
        year = int(numeric_month_year.group(2))
        if year < 100:
            year += 2000
        try:
            return date(year, month, 1)
        except ValueError:
            return None

    if re.fullmatch(r"\d{4}", value):
        return date(int(value), 1, 1)

    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Repara fechas de extintores desde CSV")
    parser.add_argument("--tenant-id", type=int, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    args = parser.parse_args()

    if args.tenant_id <= 0:
        raise SystemExit("ERROR: tenant-id debe ser mayor que cero.")
    if not args.csv.is_file():
        raise SystemExit(f"ERROR: no existe el CSV: {args.csv}")

    reader = csv.DictReader(io.StringIO(read_csv_text(args.csv)), delimiter=";")
    if reader.fieldnames is None:
        raise SystemExit("ERROR: el CSV no tiene encabezados.")
    reader.fieldnames = [normalize_header(field) for field in reader.fieldnames]

    db = SessionLocal()
    updated = 0
    missing = 0
    parsed_by_field = {field: 0 for field in DATE_FIELDS.values()}

    try:
        set_rls_tenant(db, args.tenant_id)

        for row_number, raw_row in enumerate(reader, start=2):
            row = {
                normalize_header(key): normalize_value(value)
                for key, value in raw_row.items()
                if key is not None
            }
            code = normalize_value(row.get("ID")).upper()
            if not code:
                continue

            extinguisher = (
                db.query(ExtinguisherDB)
                .filter(
                    ExtinguisherDB.tenant_id == args.tenant_id,
                    ExtinguisherDB.code == code,
                )
                .one_or_none()
            )
            if extinguisher is None:
                raise ValueError(
                    f"Fila {row_number}: no existe el extintor '{code}' en tenant {args.tenant_id}."
                )

            row_changed = False
            for model_field, csv_field in DATE_FIELDS.items():
                raw_value = row.get(csv_field)
                parsed = parse_date(raw_value)
                if raw_value and parsed is not None:
                    setattr(extinguisher, model_field, parsed)
                    parsed_by_field[csv_field] += 1
                    row_changed = True
                elif raw_value:
                    missing += 1

            if row_changed:
                updated += 1

        db.commit()

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"Extintores actualizados: {updated}")
    print(f"Valores de fecha interpretados: {sum(parsed_by_field.values())}")
    for field, count in parsed_by_field.items():
        print(f"- {field}: {count}")
    print(f"Valores de fecha no interpretables: {missing}")
    print("Reparación de fechas completada correctamente.")


if __name__ == "__main__":
    main()
