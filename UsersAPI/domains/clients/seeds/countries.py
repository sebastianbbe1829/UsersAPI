from sqlalchemy.orm import Session

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


def seed_countries(db: Session) -> tuple[int, int]:
    country = db.query(CountryDB).filter(CountryDB.code == "CO").first()
    if country is None:
        db.add(CountryDB(**COLOMBIA))
        db.flush()
        return 1, 0

    changed = False
    for field, value in COLOMBIA.items():
        if getattr(country, field) != value:
            setattr(country, field, value)
            changed = True
    return 0, int(changed)
