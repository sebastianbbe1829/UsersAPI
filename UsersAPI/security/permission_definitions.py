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
    # ========================================================
    # CONFIG UI
    # ========================================================
    (
        "CONFIG_UI_CREATE",
        "Crear configuración de UI",
        "Permite crear configuración de UI",
    ),
    (
        "CONFIG_UI_READ",
        "Consultar configuración de UI",
        "Permite consultar la configuración de UI",
    ),
    (
        "CONFIG_UI_UPDATE",
        "Actualizar configuración de UI",
        "Permite actualizar la configuración de UI",
    ),
    # ========================================================
    # EXTINTORES
    # ========================================================
    (
        "EXTINGUISHER_READ",
        "Consultar extintores",
        "Permite consultar extintores",
    ),
    (
        "EXTINGUISHER_CREATE",
        "Crear extintores",
        "Permite crear extintores",
    ),
    (
        "EXTINGUISHER_UPDATE",
        "Actualizar extintores",
        "Permite actualizar extintores",
    ),
    (
        "EXTINGUISHER_DELETE",
        "Desactivar extintores",
        "Permite desactivar extintores",
    ),

    # ========================================================
    # CLIENTES
    # ========================================================
    (
        "CLIENT_READ",
        "Consultar clientes",
        "Permite consultar clientes",
    ),
    (
        "CLIENT_CREATE",
        "Crear clientes",
        "Permite crear clientes",
    ),
    (
        "CLIENT_UPDATE",
        "Actualizar clientes",
        "Permite actualizar clientes",
    ),
    (
        "CLIENT_DELETE",
        "Eliminar clientes",
        "Permite eliminar clientes",
    ),
    (
        "CLIENT_SCREENING",
        "Consultar compliance de clientes",
        "Permite consultar el estado de compliance de clientes",
    ),
]
