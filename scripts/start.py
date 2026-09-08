"""Application startup orchestration for migrations, seeds, and API server."""

import subprocess
import sys

import uvicorn

from UsersAPI.settings import settings
from scripts.bootstrap_clients import bootstrap_clients
from scripts.seed_permissions import seed_permissions
from UsersAPI.database import SessionLocal


def run_migrations() -> None:
    """Apply pending Alembic migrations."""
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
    )


def run_initialization() -> None:
    """Run idempotent application seeds/bootstrap routines."""
    seed_permissions()

    db = SessionLocal()
    try:
        result = bootstrap_clients(db)
        print(f"Bootstrap CLIENTS: {result}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def start_api() -> None:
    """Start the FastAPI application."""
    uvicorn.run(
        "UsersAPI.main:app",
        host="0.0.0.0",
        port=settings.port,
    )


def main() -> None:
    """Run all startup steps in the required order."""
    print("==> Aplicando migraciones...")
    run_migrations()

    print("==> Ejecutando inicialización...")
    run_initialization()

    print(f"==> Iniciando API en el puerto {settings.port}...")
    start_api()


if __name__ == "__main__":
    main()
