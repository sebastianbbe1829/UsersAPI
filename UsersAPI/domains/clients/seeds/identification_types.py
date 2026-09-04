from sqlalchemy.orm import Session

from UsersAPI.domains.clients.models import IdentificationTypeDB


IDENTIFICATION_TYPES = [
    ("RC", "Registro civil", "NATURAL"),
    ("TI", "Tarjeta de identidad", "NATURAL"),
    ("CC", "Cédula de ciudadanía", "NATURAL"),
    ("TE", "Tarjeta de extranjería", "NATURAL"),
    ("CE", "Cédula de extranjería", "NATURAL"),
    ("NIT", "Número de identificación tributaria", "JURIDICA"),
    ("PP", "Pasaporte", "NATURAL"),
    ("PEP", "Permiso especial de permanencia", "NATURAL"),
    ("DIE", "Documento de identificación extranjero", "NATURAL"),
    ("NUIP", "NUIP", "NATURAL"),
    ("FOREIGN_NIT", "NIT de otro país", "JURIDICA"),
]


def seed_identification_types(db: Session) -> tuple[int, int, int]:
    official_codes = {code for code, _, _ in IDENTIFICATION_TYPES}
    created = updated = deactivated = 0

    for code, name, person_type in IDENTIFICATION_TYPES:
        item = (
            db.query(IdentificationTypeDB)
            .filter(IdentificationTypeDB.code == code)
            .first()
        )
        if item is None:
            db.add(
                IdentificationTypeDB(
                    code=code,
                    name=name,
                    person_type=person_type,
                    active=True,
                )
            )
            created += 1
            continue

        changed = (
            item.name != name
            or item.person_type != person_type
            or item.active is not True
        )
        item.name = name
        item.person_type = person_type
        item.active = True
        updated += int(changed)

    for item in db.query(IdentificationTypeDB).all():
        if item.code not in official_codes and item.active:
            item.active = False
            deactivated += 1

    return created, updated, deactivated
