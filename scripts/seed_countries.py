from UsersAPI.database import SessionLocal
from UsersAPI.domains.clients.models.catalogs import CountryDB


COLOMBIA = {
    "code": "CO",
    "name": "COLOMBIA",
    "short_name_lower": "Colombia",
    "full_name": "the Republic of Colombia",
    "alpha3_code": "COL",
    "numeric_code": 170,
    "remarks": None,
    "independent": True,
    "territory_name": "Malpelo Island, San Andrés y Providencia Islands",
    "status": "Officially assigned",
    "active": True,
}


def seed_countries() -> None:
    db = SessionLocal()
    try:
        country = db.query(CountryDB).filter(CountryDB.code == "CO").first()
        if country is None:
            country = CountryDB(**COLOMBIA)
            db.add(country)
            action = "creado"
        else:
            for field, value in COLOMBIA.items():
                setattr(country, field, value)
            action = "actualizado"

        db.commit()
        print(f"Colombia {action}: CO / COL / 170")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_countries()
