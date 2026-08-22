import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker


# ============================================================
# VARIABLES DE ENTORNO
# ============================================================

load_dotenv(
    Path(__file__).resolve().parents[1] / ".env",
    override=True,
)


# ============================================================
# DATABASE URL - APLICACIÓN NORMAL
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL no está configurada."
    )


# ============================================================
# DATABASE URL - BOOTSTRAP
# ============================================================

BOOTSTRAP_DATABASE_URL = os.getenv(
    "BOOTSTRAP_DATABASE_URL"
)

if not BOOTSTRAP_DATABASE_URL:
    raise RuntimeError(
        "BOOTSTRAP_DATABASE_URL no está configurada."
    )


# ============================================================
# ENGINE - APLICACIÓN NORMAL
# ============================================================

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
)


# ============================================================
# ENGINE - BOOTSTRAP
#
# Esta conexión utiliza el usuario PostgreSQL destinado
# exclusivamente al proceso de bootstrap.
#
# Ese usuario tendrá BYPASSRLS.
# ============================================================

bootstrap_engine = create_engine(
    BOOTSTRAP_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
)


# ============================================================
# SESSION - APLICACIÓN NORMAL
# ============================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ============================================================
# SESSION - BOOTSTRAP
# ============================================================

BootstrapSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=bootstrap_engine,
)


# ============================================================
# BASE
# ============================================================

Base = declarative_base()


# ============================================================
# RLS - CONTEXTO DEL TENANT
# ============================================================

def set_rls_tenant(
    db,
    tenant_id: int,
) -> None:

    db.execute(
        text(
            """
            SELECT set_config(
                'app.current_tenant_id',
                :tenant_id,
                true
            )
            """
        ),
        {
            "tenant_id": str(tenant_id),
        },
    )


# ============================================================
# DATABASE DEPENDENCY
#
# Utilizada por los endpoints normales de la aplicación.
#
# Esta conexión utiliza DATABASE_URL y, por tanto,
# permanece protegida por RLS.
# ============================================================

def get_db():

    db = SessionLocal()

    try:
        yield db
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ============================================================
# BOOTSTRAP DATABASE DEPENDENCY
#
# Utilizada exclusivamente por /bootstrap.
#
# Esta conexión utiliza BOOTSTRAP_DATABASE_URL.
# ============================================================

def get_bootstrap_db():

    db = BootstrapSessionLocal()

    try:
        yield db
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()