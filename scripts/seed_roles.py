from UsersAPI.database import SessionLocal
from UsersAPI.models import RoleDB


ROLES = [
    (
        "SUPER_ADMIN",
        "Super Administrador",
        "Administrador global con acceso completo al sistema.",
    ),
    (
        "SYSTEM_ADMIN",
        "Administrador del Sistema",
        "Administrador global para tareas técnicas y de configuración.",
    ),
]


def seed_roles():
    db = SessionLocal()

    try:
        creados = 0
        existentes = 0

        for code, name, description in ROLES:

            role = (
                db.query(RoleDB)
                .filter(
                    RoleDB.tenant_id.is_(None),
                    RoleDB.code == code,
                )
                .first()
            )

            if role:
                existentes += 1
                continue

            role = RoleDB(
                tenant_id=None,
                code=code,
                name=name,
                description=description,
                status=1,
                created_by="SYSTEM",
            )

            db.add(role)
            creados += 1

        db.commit()

        print(f"Roles creados: {creados}")
        print(f"Roles existentes: {existentes}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_roles()