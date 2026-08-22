from UsersAPI.database import SessionLocal
from UsersAPI.models import PermissionDB
from UsersAPI.security.permission_definitions import PERMISSIONS


# ============================================================
# SEED DE PERMISOS
# ============================================================

def seed_permissions():
    db = SessionLocal()

    try:

        creados = 0
        existentes = 0

        # ====================================================
        # RECORRER DEFINICIÓN DE PERMISOS
        # ====================================================

        for code, name, description in PERMISSIONS:

            permission = (
                db.query(PermissionDB)
                .filter(
                    PermissionDB.code == code
                )
                .first()
            )

            # =================================================
            # YA EXISTE
            # =================================================

            if permission:

                existentes += 1

                continue

            # =================================================
            # CREAR PERMISO
            # =================================================

            permission = PermissionDB(
                code=code,
                name=name,
                description=description,
                status=1,
                created_by="SYSTEM",
            )

            db.add(permission)

            creados += 1

        # ====================================================
        # COMMIT
        # ====================================================

        db.commit()

        print(
            f"Permisos creados: {creados}"
        )

        print(
            f"Permisos existentes: {existentes}"
        )

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()


# ============================================================
# EJECUCIÓN DIRECTA
# ============================================================

if __name__ == "__main__":

    seed_permissions()