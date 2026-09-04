"""CLI entry point for initializing the CLIENTS domain."""

from pprint import pprint

from UsersAPI.database import SessionLocal
from UsersAPI.domains.clients.seeds.bootstrap import bootstrap_clients


if __name__ == "__main__":
    db = SessionLocal()
    try:
        result = bootstrap_clients(db)
        pprint(result)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
