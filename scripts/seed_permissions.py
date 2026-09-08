from UsersAPI.database import SessionLocal
from UsersAPI.models import PermissionDB
from UsersAPI.security.inventory_permissions import INVENTORY_PERMISSIONS
from UsersAPI.security.permission_definitions import PERMISSIONS


# ============================================================
# SEED DE PERMISOS
# ============================================================

def seed_permissions():
    db = SessionLocal()
    permission_definitions = [*PERMISSIONS, *INVENTORY_PERMISSIONS]

    try:
        creados = 0
        existentes = 0

        for code, name, description in permission_definitions:
            permission = (
                db.query(PermissionDB)
                .filter(PermissionDB.code == code)
                .first()
            )

            if permission:
                existentes += 1
                continue

            db.add(
                PermissionDB(
                    code=code,
                    name=name,
                    description=description,
                    status=1,
                    created_by="SYSTEM",
                )
            )
            creados += 1

        db.commit()
        print(f"Permisos creados: {creados}")
        print(f"Permisos existentes: {existentes}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_permissions()
