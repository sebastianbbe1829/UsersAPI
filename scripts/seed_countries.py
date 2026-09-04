"""CLI compatibility wrapper for the CLIENTS country seeder."""

from UsersAPI.database import SessionLocal
from UsersAPI.domains.clients.seeds.countries import seed_countries


if __name__ == "__main__":
    db = SessionLocal()
    try:
        created, updated = seed_countries(db)
        db.commit()
        print(f"Países: creados={created}, actualizados={updated}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
