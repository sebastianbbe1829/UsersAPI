from UsersAPI.database import SessionLocal
from UsersAPI.models import PermissionDB


PERMISSIONS = [
    # ============================================================
    # USUARIOS
    # ============================================================

    (
        "USER_READ",
        "Consultar usuarios",
        "Permite consultar usuarios",
    ),
    (
        "USER_CREATE",
        "Crear usuarios",
        "Permite crear usuarios",
    ),
    (
        "USER_UPDATE",
        "Actualizar usuarios",
        "Permite actualizar usuarios",
    ),
    (
        "USER_DELETE",
        "Eliminar usuarios",
        "Permite eliminar usuarios",
    ),
    (
        "USER_EXPORT",
        "Exportar usuarios",
        "Permite exportar usuarios",
    ),

    # ============================================================
    # TENANTS
    # ============================================================

    (
        "TENANT_READ",
        "Consultar empresas",
        "Permite consultar empresas",
    ),
    (
        "TENANT_CREATE",
        "Crear empresas",
        "Permite crear empresas",
    ),
    (
        "TENANT_UPDATE",
        "Actualizar empresas",
        "Permite actualizar empresas",
    ),
    (
        "TENANT_DELETE",
        "Eliminar empresas",
        "Permite eliminar empresas",
    ),

    # ============================================================
    # ROLES
    # ============================================================

    (
        "ROLE_READ",
        "Consultar roles",
        "Permite consultar roles",
    ),
    (
        "ROLE_CREATE",
        "Crear roles",
        "Permite crear roles",
    ),
    (
        "ROLE_UPDATE",
        "Actualizar roles",
        "Permite actualizar roles",
    ),
    (
        "ROLE_DELETE",
        "Eliminar roles",
        "Permite eliminar roles",
    ),

    # ============================================================
    # PERMISOS
    # ============================================================

    (
        "PERMISSION_READ",
        "Consultar permisos",
        "Permite consultar permisos",
    ),
    (
        "PERMISSION_CREATE",
        "Crear permisos",
        "Permite crear permisos",
    ),
    (
        "PERMISSION_UPDATE",
        "Actualizar permisos",
        "Permite actualizar permisos",
    ),
    (
        "PERMISSION_DELETE",
        "Eliminar permisos",
        "Permite eliminar permisos",
    ),
    (
        "AUTHENTICATE",
        "Autenticación",
        "Permite la autenticación en el sistema",
    ),
]


def seed_permissions():
    db = SessionLocal()

    try:
        creados = 0
        existentes = 0

        for code, name, description in PERMISSIONS:

            permission = (
                db.query(PermissionDB)
                .filter(PermissionDB.code == code)
                .first()
            )

            if permission:
                existentes += 1
                continue

            permission = PermissionDB(
                code=code,
                name=name,
                description=description,
                status=1,
                created_by="SYSTEM",
            )

            db.add(permission)
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