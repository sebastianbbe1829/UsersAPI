# ============================================================
# DEFINICIÓN DE PERMISOS DEL SISTEMA
# ============================================================

PERMISSIONS = [
    # ========================================================
    # USUARIOS
    # ========================================================

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

    # ========================================================
    # TENANTS
    # ========================================================

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

    # ========================================================
    # ROLES
    # ========================================================

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

    # ========================================================
    # PERMISOS
    # ========================================================

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
      # ========================================================
    # AUTENTICACIÓN
    # ========================================================

    (
        "AUTHENTICATE",
        "Autenticación",
        "Permite la autenticación en el sistema",
    ),
]