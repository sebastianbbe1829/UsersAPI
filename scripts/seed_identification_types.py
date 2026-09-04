"""CLI compatibility wrapper for the CLIENTS identification type seeder."""

from UsersAPI.database import SessionLocal
from UsersAPI.domains.clients.seeds.identification_types import seed_identification_types


if __name__ == "__main__":
    db = SessionLocal()
    try:
        created, updated, deactivated = seed_identification_types(db)
        db.commit()
        print(
            "Identification types: "
            f"created={created}, updated={updated}, deactivated={deactivated}"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
