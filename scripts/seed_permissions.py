from sqlalchemy import func

from UsersAPI.database import SessionLocal
from UsersAPI.models import PermissionDB, RoleDB, RolePermissionDB
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

        # ====================================================
        # CREAR / VALIDAR PERMISOS
        # ====================================================

        permissions_by_code = {}

        for code, name, description in permission_definitions:
            permission = (
                db.query(PermissionDB)
                .filter(PermissionDB.code == code)
                .first()
            )

            if permission:
                existentes += 1
                permissions_by_code[code] = permission
                continue

            permission = PermissionDB(
                code=code,
                name=name,
                description=description,
                status=1,
                created_by="SYSTEM",
            )
            db.add(permission)
            db.flush()

            permissions_by_code[code] = permission
            creados += 1

        # ====================================================
        # SINCRONIZAR PERMISOS DEL ADMIN EXISTENTE
        # ====================================================
        # El servicio de roles permite que un rol creado originalmente
        # como ADMIN termine almacenado como "admin" al actualizarlo.
        # La sincronización debe reconocer ambos casos sin depender
        # de mayúsculas/minúsculas. También reconocemos el nombre
        # histórico "Administrador" para no dejar tenants existentes
        # sin sincronización por una diferencia de código.
        roles_admin = (
            db.query(RoleDB)
            .filter(
                RoleDB.status != 3,
                (
                    func.upper(RoleDB.code) == "ADMIN"
                )
                | (
                    func.lower(RoleDB.name) == "administrador"
                ),
            )
            .all()
        )

        asignados = 0
        for admin_role in roles_admin:
            permisos_actuales = {
                role_permission.permission_id
                for role_permission in db.query(RolePermissionDB).filter(
                    RolePermissionDB.role_id == admin_role.id
                ).all()
            }

            for permission in permissions_by_code.values():
                if permission.id in permisos_actuales:
                    continue

                db.add(
                    RolePermissionDB(
                        role_id=admin_role.id,
                        permission_id=permission.id,
                    )
                )
                asignados += 1

        # ====================================================
        # COMMIT
        # ====================================================

        db.commit()

        print(f"Permisos creados: {creados}")
        print(f"Permisos existentes: {existentes}")
        print(f"Roles ADMIN encontrados: {len(roles_admin)}")
        print(f"Permisos asignados a ADMIN: {asignados}")

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
