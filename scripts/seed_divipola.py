"""CLI compatibility wrapper for the CLIENTS DIVIPOLA seeder."""

from UsersAPI.database import SessionLocal
from UsersAPI.domains.clients.seeds.divipola import seed_divipola


if __name__ == "__main__":
    db = SessionLocal()
    try:
        result = seed_divipola(db)
        db.commit()
        for key, value in result.items():
            print(f"{key}: {value}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
