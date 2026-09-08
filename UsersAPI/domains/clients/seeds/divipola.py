import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy.orm import Session

from UsersAPI.domains.clients.models.catalogs import CityDB, CountryDB, DepartmentDB


BASE_DIR = Path(__file__).resolve().parents[4]
DEFAULT_CSV_PATH = BASE_DIR / "data" / "DIVIPOLA.csv"

COLUMN_DEPARTMENT_CODE = "Código Departamento"
COLUMN_DEPARTMENT_NAME = "Nombre Departamento"
COLUMN_MUNICIPALITY_CODE = "Código Municipio"
COLUMN_MUNICIPALITY_NAME = "Nombre Municipio"
COLUMN_TYPE = "Tipo: Municipio / Isla / Área no municipalizada"
COLUMN_LONGITUDE = "longitud"
COLUMN_LATITUDE = "Latitud"


def normalizar_codigo(valor: str, longitud: int) -> str:
    codigo = (valor or "").strip()
    if not codigo:
        raise ValueError("Se encontró un código DANE vacío.")
    return codigo.zfill(longitud)


def parsear_coordenada(valor: str) -> Decimal | None:
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        return Decimal(valor.replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError(f"Coordenada inválida: {valor!r}") from exc


def validar_fila(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    department_code = normalizar_codigo(row.get(COLUMN_DEPARTMENT_CODE, ""), 2)
    municipality_code = normalizar_codigo(row.get(COLUMN_MUNICIPALITY_CODE, ""), 5)
    department_name = (row.get(COLUMN_DEPARTMENT_NAME) or "").strip()
    municipality_name = (row.get(COLUMN_MUNICIPALITY_NAME) or "").strip()
    unit_type = (row.get(COLUMN_TYPE) or "").strip()

    if not department_name or not municipality_name or not unit_type:
        raise ValueError(f"Fila DIVIPOLA incompleta: {row}")
    if not municipality_code.startswith(department_code):
        raise ValueError(
            "Código municipio "
            f"{municipality_code} no corresponde al departamento "
            f"{department_code}."
        )
    return department_code, municipality_code, department_name, municipality_name, unit_type


def seed_divipola(db: Session, csv_path: Path = DEFAULT_CSV_PATH) -> dict[str, int]:
    if not csv_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo DIVIPOLA: {csv_path}")

    country = db.query(CountryDB).filter(CountryDB.code == "CO").first()
    if country is None:
        raise RuntimeError("No existe el país CO - Colombia. Ejecute primero el seed de países.")
    if not country.active:
        raise RuntimeError("El país CO - Colombia está inactivo y no puede recibir DIVIPOLA.")

    result = {
        "filas": 0,
        "departamentos_creados": 0,
        "departamentos_actualizados": 0,
        "ciudades_creadas": 0,
        "ciudades_actualizadas": 0,
    }

    # Cargar los catálogos existentes una sola vez. El seed anterior hacía
    # consultas individuales de departamento y ciudad para cada fila del CSV.
    departments = (
        db.query(DepartmentDB)
        .filter(DepartmentDB.country_id == country.id)
        .all()
    )
    departments_by_code = {department.code: department for department in departments}

    cities = (
        db.query(CityDB)
        .join(DepartmentDB, CityDB.department_id == DepartmentDB.id)
        .filter(DepartmentDB.country_id == country.id)
        .all()
    )
    cities_by_key = {
        (city.department_id, city.code): city
        for city in cities
    }

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        expected_columns = {
            COLUMN_DEPARTMENT_CODE,
            COLUMN_DEPARTMENT_NAME,
            COLUMN_MUNICIPALITY_CODE,
            COLUMN_MUNICIPALITY_NAME,
            COLUMN_TYPE,
            COLUMN_LONGITUDE,
            COLUMN_LATITUDE,
        }
        missing_columns = expected_columns - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(
                "El archivo DIVIPOLA no contiene las columnas esperadas: "
                + ", ".join(sorted(missing_columns))
            )

        for row in reader:
            result["filas"] += 1
            (
                department_code,
                municipality_code,
                department_name,
                municipality_name,
                unit_type,
            ) = validar_fila(row)

            department = departments_by_code.get(department_code)
            if department is None:
                department = DepartmentDB(
                    country_id=country.id,
                    code=department_code,
                    name=department_name,
                    active=True,
                )
                db.add(department)
                db.flush()
                departments_by_code[department_code] = department
                result["departamentos_creados"] += 1
            else:
                changed = department.name != department_name or not department.active
                department.name = department_name
                department.active = True
                result["departamentos_actualizados"] += int(changed)

            latitude = parsear_coordenada(row.get(COLUMN_LATITUDE, ""))
            longitude = parsear_coordenada(row.get(COLUMN_LONGITUDE, ""))
            city_key = (department.id, municipality_code)
            city = cities_by_key.get(city_key)

            if city is None:
                city = CityDB(
                    department_id=department.id,
                    code=municipality_code,
                    name=municipality_name,
                    type=unit_type,
                    latitude=latitude,
                    longitude=longitude,
                    active=True,
                )
                db.add(city)
                cities_by_key[city_key] = city
                result["ciudades_creadas"] += 1
            else:
                city.name = municipality_name
                city.type = unit_type
                city.latitude = latitude
                city.longitude = longitude
                city.active = True
                result["ciudades_actualizadas"] += 1

    return result
