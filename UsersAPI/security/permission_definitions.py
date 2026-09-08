# ============================================================
# DEFINICIÓN DE PERMISOS DEL SISTEMA
# ============================================================

PERMISSIONS = [
    ("USER_READ", "Consultar usuarios", "Permite consultar usuarios"),
    ("USER_CREATE", "Crear usuarios", "Permite crear usuarios"),
    ("USER_UPDATE", "Actualizar usuarios", "Permite actualizar usuarios"),
    ("USER_DELETE", "Eliminar usuarios", "Permite eliminar usuarios"),
    ("USER_EXPORT", "Exportar usuarios", "Permite exportar usuarios"),
    ("TENANT_READ", "Consultar empresas", "Permite consultar empresas"),
    ("TENANT_CREATE", "Crear empresas", "Permite crear empresas"),
    ("TENANT_UPDATE", "Actualizar empresas", "Permite actualizar empresas"),
    ("TENANT_DELETE", "Eliminar empresas", "Permite eliminar empresas"),
    ("ROLE_READ", "Consultar roles", "Permite consultar roles"),
    ("ROLE_CREATE", "Crear roles", "Permite crear roles"),
    ("ROLE_UPDATE", "Actualizar roles", "Permite actualizar roles"),
    ("ROLE_DELETE", "Eliminar roles", "Permite eliminar roles"),
    ("PERMISSION_READ", "Consultar permisos", "Permite consultar permisos"),
    ("PERMISSION_CREATE", "Crear permisos", "Permite crear permisos"),
    ("AUTHENTICATE", "Autenticación", "Permite la autenticación en el sistema"),
    ("CONFIG_UI_CREATE", "Crear configuración de UI", "Permite crear configuración de UI"),
    ("CONFIG_UI_READ", "Consultar configuración de UI", "Permite consultar la configuración de UI"),
    (
        "CONFIG_UI_UPDATE",
        "Actualizar configuración de UI",
        "Permite actualizar configuración de UI",
    ),
    ("EXTINGUISHER_READ", "Consultar extintores", "Permite consultar extintores"),
    ("EXTINGUISHER_CREATE", "Crear extintores", "Permite crear extintores"),
    ("EXTINGUISHER_UPDATE", "Actualizar extintores", "Permite actualizar extintores"),
    ("EXTINGUISHER_DELETE", "Desactivar extintores", "Permite desactivar extintores"),
    ("CLIENT_READ", "Consultar clientes", "Permite consultar clientes"),
    ("CLIENT_CREATE", "Crear clientes", "Permite crear clientes"),
    ("CLIENT_UPDATE", "Actualizar clientes", "Permite actualizar clientes"),
    ("CLIENT_DELETE", "Eliminar clientes", "Permite eliminar clientes"),
    (
        "CLIENT_SCREENING",
        "Consultar compliance de clientes",
        "Permite consultar el estado de compliance de clientes",
    ),
    (
        "CLIENT_COMPLIANCE_OVERRIDE",
        "Levantar restricción de cliente",
        "Permite levantar una restricción de compliance mediante autorización",
    ),
    (
        "SALES_READ",
        "Consultar ventas",
        "Permite consultar ventas y sus detalles",
    ),
    (
        "SALES_CREATE",
        "Crear ventas",
        "Permite registrar ventas y afectar el inventario",
    ),
    (
        "SALES_EMAIL",
        "Enviar factura por correo",
        "Permite enviar la factura de una venta a los clientes registrados",
    ),
    (
        "PORTFOLIO_READ",
        "Consultar cartera",
        "Permite consultar cupos, obligaciones y pagos de cartera",
    ),
    (
        "PORTFOLIO_CREDIT_UPDATE",
        "Administrar cupos",
        "Permite crear y actualizar el cupo de los clientes",
    ),
    (
        "PORTFOLIO_PAYMENT_CREATE",
        "Registrar pagos de cartera",
        "Permite registrar pagos y aplicarlos a obligaciones",
    ),
]
