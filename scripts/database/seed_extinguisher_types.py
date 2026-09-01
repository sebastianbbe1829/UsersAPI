from sqlalchemy.orm import Session

from UsersAPI.database import engine
from UsersAPI.models import ExtinguisherTypeDB


INITIAL_TYPES = [
    ("POLVO_QUIMICO_SECO", "Polvo químico seco (PQS)"),
    ("CO2", "Dióxido de carbono (CO₂)"),
    ("AGUA", "Agua"),
    ("ESPUMA", "Espuma"),
    ("AGENTE_LIMPIO", "Agente limpio"),
]


def seed() -> None:
    with Session(engine) as db:
        for code, name in INITIAL_TYPES:
            item = db.query(ExtinguisherTypeDB).filter(ExtinguisherTypeDB.code == code).first()
            if item is None:
                db.add(ExtinguisherTypeDB(code=code, name=name, active=True))
            else:
                item.name = name
                item.active = True
        db.commit()
    print(f"Tipos de extintor iniciales aplicados: {len(INITIAL_TYPES)}")


if __name__ == "__main__":
    seed()
