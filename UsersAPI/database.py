import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
# DATABASE_URL = f"sqlite:///{BASE_DIR / 'usuarios.db'}"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "oracle+oracledb://USER_MAL:ClaveMala@192.168.1.73:1521/?service_name=xepdb1",
)


# engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()