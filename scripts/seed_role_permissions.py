from UsersAPI.database import SessionLocal
from UsersAPI.models import (
    RoleDB,
    PermissionDB,
    RolePermissionDB,
)


# ============================================================
# PERMISOS POR ROL
# ============================================================

ROLE_PERMISSIONS = {
    "SUPER_ADMIN": "ALL",

    "SYSTEM_ADMIN": [
        "USER_READ",
        "USER_CREATE",
        "USER_UPDATE",
        "USER_DELETE",
        "USER_EXPORT",

        "TENANT_READ",
        "TENANT_CREATE",
        "TENANT_UPDATE",

        "ROLE_READ",
        "ROLE_CREATE",
        "ROLE_UPDATE",

        "PERMISSION_READ",
        "PERMISSION_CREATE",
        "PERMISSION_UPDATE",
    ],

    "CONSULTA": [
        "USER_READ",
        "USER_EXPORT",

        "TENANT_READ",

        "ROLE_READ",

        "PERMISSION_READ",
    ],
}


# ============================================================
# ROLES GLOBALES
# ============================================================

GLOBAL_ROLES = [
    "SUPER_ADMIN",
    "SYSTEM_ADMIN",
]


def get_permissions(db):
    """
    Retorna todos los permisos activos indexados por código.
    """

    permissions = (
        db.query(PermissionDB)
        .filter(PermissionDB.status == 1)
        .all()
    )

    return {
        permission.code: permission
        for permission in permissions
    }


def get_role(db, role_code: str, tenant_id=None):
    """
    Busca un rol respetando su alcance.

    tenant_id=None
        → rol global

    tenant_id=<id>
        → rol perteneciente a ese tenant
    """

    return (
        db.query(RoleDB)
        .filter(
            RoleDB.code == role_code,
            RoleDB.tenant_id == tenant_id,
            RoleDB.status == 1,
        )
        .first()
    )


def assign_permissions(
    db,
    role: RoleDB,
    permission_map: dict,
):
    """
    Asigna los permisos definidos al rol.
    """

    permission_codes = ROLE_PERMISSIONS[role.code]

    if permission_codes == "ALL":
        permissions = list(permission_map.values())

    else:
        permissions = []

        for code in permission_codes:

            permission = permission_map.get(code)

            if permission is None:
                raise RuntimeError(
                    f"El permiso '{code}' no existe en la BD."
                )

            permissions.append(permission)

    creados = 0
    existentes = 0

    for permission in permissions:

        relation = (
            db.query(RolePermissionDB)
            .filter(
                RolePermissionDB.role_id == role.id,
                RolePermissionDB.permission_id == permission.id,
            )
            .first()
        )

        if relation:
            existentes += 1
            continue

        db.add(
            RolePermissionDB(
                role_id=role.id,
                permission_id=permission.id,
            )
        )

        creados += 1

    return creados, existentes


def seed_global_roles(db, permission_map):
    """
    Crea los roles globales y asigna sus permisos.
    """

    total_creados = 0
    total_existentes = 0

    for role_code in GLOBAL_ROLES:

        role = get_role(
            db,
            role_code,
            tenant_id=None,
        )

        if role is None:

            role = RoleDB(
                tenant_id=None,
                code=role_code,
                name=(
                    "Super Administrador"
                    if role_code == "SUPER_ADMIN"
                    else "Administrador del Sistema"
                ),
                description=(
                    "Administrador global con acceso completo al sistema."
                    if role_code == "SUPER_ADMIN"
                    else "Administrador global para tareas técnicas y de configuración."
                ),
                status=1,
                created_by="SYSTEM",
            )

            db.add(role)
            db.flush()

            print(f"Rol global creado: {role_code}")

        else:

            print(f"Rol global existente: {role_code}")

        creados, existentes = assign_permissions(
            db,
            role,
            permission_map,
        )

        total_creados += creados
        total_existentes += existentes

    return total_creados, total_existentes


def seed_tenant_role(
    db,
    permission_map,
    tenant_id: int,
):
    """
    Crea el rol CONSULTA para un tenant específico.
    """

    role = get_role(
        db,
        "CONSULTA",
        tenant_id=tenant_id,
    )

    if role is None:

        role = RoleDB(
            tenant_id=tenant_id,
            code="CONSULTA",
            name="Consulta",
            description=(
                "Permite consultar información y exportar usuarios "
                "sin modificar información."
            ),
            status=1,
            created_by="SYSTEM",
        )

        db.add(role)
        db.flush()

        print(
            f"Rol CONSULTA creado para tenant {tenant_id}"
        )

    else:

        print(
            f"Rol CONSULTA ya existe para tenant {tenant_id}"
        )

    return assign_permissions(
        db,
        role,
        permission_map,
    )


def seed_role_permissions():
    db = SessionLocal()

    try:

        permission_map = get_permissions(db)

        if not permission_map:

            raise RuntimeError(
                "No existen permisos activos. "
                "Ejecute primero seed_permissions."
            )

        creados, existentes = seed_global_roles(
            db,
            permission_map,
        )

        db.commit()

        print()
        print("========================================")
        print("SEED DE ROLES Y PERMISOS")
        print("========================================")
        print(f"Asignaciones creadas: {creados}")
        print(f"Asignaciones existentes: {existentes}")
        print("========================================")

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


if __name__ == "__main__":
    seed_role_permissions()