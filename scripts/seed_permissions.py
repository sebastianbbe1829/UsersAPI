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
        # SINCRONIZAR PERMISOS DE ROLES ADMIN EXISTENTES
        # ====================================================
        # El bootstrap de un tenant nuevo asigna todos los permisos
        # al rol ADMIN. Este seed debe mantener el mismo contrato
        # para tenants ya existentes cuando se agregan permisos nuevos.
        #
        # Importante: no usamos la relación ORM admin_role.permissions
        # para determinar los existentes. Consultamos directamente
        # role_permissions para que la sincronización dependa de la
        # relación persistida en BD y sea completamente idempotente.

        roles_admin = (
            db.query(RoleDB)
            .filter(
                RoleDB.code == "ADMIN",
                RoleDB.status != 3,
            )
            .all()
        )

        asignados = 0
        for admin_role in roles_admin:
            permisos_actuales = {
                permission_id
                for (permission_id,) in (
                    db.query(RolePermissionDB.permission_id)
                    .filter(RolePermissionDB.role_id == admin_role.id)
                    .all()
                )
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
                permisos_actuales.add(permission.id)
                asignados += 1

        # ====================================================
        # COMMIT
        # ====================================================

        db.commit()

        print(f"Permisos creados: {creados}")
        print(f"Permisos existentes: {existentes}")
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
