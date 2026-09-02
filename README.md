# UsersAPI

API REST multi-tenant construida con **FastAPI, SQLAlchemy y PostgreSQL**. Provee gestión de usuarios, tenants (empresas), roles y permisos (RBAC), autenticación TENANT con JWT, autenticación administrativa SUPER con MFA, recuperación de cuentas mediante OTP y un módulo de negocio para inventario e inspección de extintores.

## Características principales

- **Multi-tenancy real:** aislamiento de datos mediante **Row-Level Security (RLS)** de PostgreSQL.
- **RBAC por tenant:** roles y permisos pertenecen al tenant; las acciones protegidas validan permisos específicos.
- **Autenticación TENANT:** login mediante credenciales del tenant y emisión de JWT con expiración configurable.
- **Autenticación SUPER:** sesión administrativa separada de las sesiones TENANT y protegida con contraseña + MFA TOTP.
- **Protección de credenciales:** passwords almacenados con hash Argon2 y secretos MFA cifrados en reposo con Fernet.
- **Recuperación y activación:** códigos OTP temporales con expiración y límite de intentos.
- **Rate limiting:** protección por IP y por cuenta en endpoints sensibles de autenticación, MFA, recuperación y bootstrap.
- **CORS restringido:** solo se permiten los orígenes configurados para el frontend local y de producción.
- **Logs sanitizados:** datos sensibles como emails, tokens, secretos, sesiones, IDs internos e IPs son redactados antes de escribirse en consola o archivo.
- **Módulo de extintores:** inventario, tipos, inspecciones, ítems de inspección, búsqueda, exportación y notificaciones.
- **Exportación a Excel:** usuarios y extintores.
- **CI:** GitHub Actions ejecuta pruebas automatizadas y análisis estático de seguridad con Bandit.

## Arquitectura

El proyecto sigue separación por capas y evita colocar lógica de negocio en los routers:

```text
routes/        → endpoints HTTP y dependencias de seguridad
controllers/   → orquestación entre HTTP y servicios
services/      → lógica de negocio
repositories/  → acceso a datos mediante SQLAlchemy
models/        → modelos ORM
schemas/       → contratos Pydantic
security/      → autenticación, autorización, JWT, RLS y rate limiting
util/          → utilidades de Excel, email y WhatsApp
```

Flujo general:

```text
Cliente → Route → Controller → Service → Repository → PostgreSQL
                                      ↘ seguridad / reglas de negocio
```

## Requisitos

- Python 3.12+
- PostgreSQL 16+
- pip

## Instalación local

```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\\Scripts\\Activate.ps1

pip install -r requirements.txt
```

Crea un archivo `.env` local con las variables necesarias. **No subas `.env` ni secretos al repositorio.**

## Variables de entorno

Las variables dependen de los módulos habilitados. Las principales son:

```text
# JWT
SECRET_KEY=<secreto aleatorio largo>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15

# Base de datos
DATABASE_URL=postgresql+psycopg://usuario:password@host:5432/db
BOOTSTRAP_DATABASE_URL=postgresql+psycopg://usuario_bootstrap:password@host:5432/db
DATABASE_ADMIN_URL=postgresql+psycopg://admin:password@host:5432/db

# Bootstrap
BOOTSTRAP_TENANT_KEY=<secreto de bootstrap>

# SUPER + MFA
SUPER_BOOTSTRAP_SECRET=<secreto de bootstrap SUPER>
SUPER_MFA_ENCRYPTION_KEY=<clave Fernet>

# Email
BREVO_API_KEY=<api key>
EMAIL_FROM=<remitente>
EMAIL_FROM_NAME=UsersAPI
EMAIL_KEY=<clave interna>
FRONTEND_URL=<url del frontend>
BACKEND_URL=<url pública del backend>
API_EMAIL_URL=<endpoint de email, si aplica>

# OTP
OTP_API_KEY=<clave interna>
OTP_LENGTH=6
OTP_EXPIRE_MINUTES=10
OTP_MAX_ATTEMPTS=5

# WhatsApp
WHATSAPP_TOKEN=<token>
WHATSAPP_PHONE_ID=<id del número>
WHATSAPP_MODE=template
WHATSAPP_API_URL=<url de la API>

# Notificaciones de extintores
EXTINGUISHER_RECHARGE_NOTIFICATIONS_ENABLED=true
EXTINGUISHER_RECHARGE_NOTIFICATION_TIME=08:00
JOB_TIMEZONE=America/Bogota
```

En producción, los secretos deben configurarse mediante el gestor de variables de entorno de la plataforma de despliegue. Nunca deben almacenarse en Git.

## Base de datos y migraciones

El proyecto usa Alembic para controlar el esquema:

```bash
alembic upgrade head
```

El aislamiento multi-tenant se apoya en **PostgreSQL RLS**. Las operaciones que trabajan bajo contexto de tenant deben establecer correctamente el tenant antes de acceder a los datos.

## Ejecutar la API

```bash
uvicorn UsersAPI.main:app --reload
```

Endpoints de disponibilidad:

- `GET /` — estado básico del servicio.
- `GET /health` — health check.

Documentación interactiva local:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## Autenticación y autorización

### Usuarios TENANT

El flujo normal es:

```text
Credenciales TENANT
        ↓
POST /auth/login
        ↓
JWT de sesión TENANT
        ↓
Autorización por tenant + rol + permiso
```

El usuario solo puede ejecutar operaciones autorizadas por los permisos asociados a sus roles dentro del tenant.

### Usuario SUPER

SUPER es una identidad administrativa separada del flujo TENANT:

```text
Credenciales SUPER
        ↓
Contraseña
        ↓
MFA TOTP
        ↓
Sesión SUPER
```

La sesión SUPER es independiente de las sesiones TENANT y permite las operaciones administrativas que requieren privilegios globales.

## RBAC

Los roles son **tenant-locales**. Un usuario puede tener asociaciones de roles diferentes en distintos tenants.

Los permisos se expresan mediante códigos, por ejemplo:

```text
USER_READ
USER_CREATE
USER_UPDATE
USER_DELETE
USER_EXPORT
ROLE_READ
ROLE_CREATE
ROLE_UPDATE
ROLE_DELETE
PERMISSION_READ
TENANT_READ
TENANT_CREATE
TENANT_UPDATE
TENANT_DELETE
AUTHENTICATE
```

El acceso a un endpoint protegido debe validarse mediante el permiso correspondiente y respetar el contexto del tenant.

## Rate limiting

Los endpoints sensibles utilizan un rate limiter de ventana deslizante en memoria. Se combinan controles por IP y por cuenta/destino cuando corresponde, y los bloqueos responden con HTTP `429` y `Retry-After`.

La configuración actual está pensada para una instancia de API. Si el servicio escala horizontalmente a múltiples instancias, el contador debe migrarse a un almacenamiento compartido como Redis para mantener límites consistentes.

El limiter utiliza `request.client.host` y no confía directamente en `X-Forwarded-For` ni `X-Real-IP`.

## CORS

En producción se permite únicamente el frontend publicado y, para desarrollo, el frontend local configurado. Los headers sensibles usados por la aplicación deben estar explícitamente incluidos en la política CORS.

La configuración actual incluye headers de autorización y los headers internos utilizados por bootstrap, OTP y email.

## Logs y seguridad operacional

Los logs de aplicación pasan por un filtro centralizado de sanitización antes de llegar a consola o archivo.

Se redactan valores sensibles como:

- passwords
- tokens
- secretos
- OTP
- Authorization
- IDs de sesión
- IDs internos de tenant
- IDs de asociación usuario-tenant
- IPs
- direcciones de email

El objetivo es conservar información útil para diagnóstico sin registrar credenciales o identificadores sensibles.

## Endpoints principales

### Usuarios

- `POST /users` — crear usuario
- `GET /users` — listar usuarios
- `GET /users/export` — exportar usuarios a Excel
- `GET /users/{dni}` — consultar usuario
- `PATCH /users/{dni}` — actualizar usuario
- `DELETE /users/{dni}` — eliminar usuario

### Autenticación

- `POST /auth/login` — iniciar sesión TENANT
- `GET /auth/validate` — validar JWT

### SUPER / MFA

Incluye endpoints para bootstrap, autenticación SUPER y verificación MFA TOTP.

### Recuperación / OTP

Incluye endpoints para solicitar y validar códigos OTP de recuperación y activación de cuenta.

### Tenants

CRUD de tenants y configuración parametrizable por tenant.

### Roles y permisos

CRUD de roles y permisos, asociación de permisos a roles y asociación de roles a usuarios dentro de cada tenant.

### Extintores

- CRUD de extintores
- Catálogo de tipos de extintor
- Inspecciones e ítems de inspección
- `GET /extinguishers/search` — búsqueda
- `GET /extinguishers/export` — exportación a Excel

La documentación OpenAPI (`/docs`) es la referencia para el listado completo de endpoints, parámetros y esquemas.

## Pruebas

Ejecutar toda la suite:

```bash
pytest -q
```

La suite incluye pruebas de autenticación, autorización, aislamiento multi-tenant/RLS, SUPER/MFA, rate limiting y seguridad de logs.

El estado esperado del Quality Gate es **cero fallos y cero warnings**.

## CI y seguridad

GitHub Actions ejecuta automáticamente la validación del proyecto, incluyendo:

- instalación de dependencias
- migraciones cuando corresponde
- `pytest -q`
- análisis estático con Bandit
- validaciones de calidad configuradas para el repositorio

Los cambios de seguridad deben pasar el Quality Gate antes de integrarse a `master`.

## Despliegue

La API se despliega como servicio web en Render.

URL de producción:

```text
https://gestion-usuarios-api.onrender.com
```

El frontend de producción utiliza el servicio de API publicado y el backend mantiene CORS restringido al origen permitido.

Para un nuevo entorno:

1. Configurar las variables de entorno sin exponer secretos.
2. Configurar `DATABASE_URL` y las credenciales necesarias.
3. Ejecutar `alembic upgrade head`.
4. Iniciar la aplicación con Uvicorn.
5. Verificar `/health`.
6. Verificar CORS desde el frontend correspondiente.
7. Ejecutar la suite de pruebas y revisar el Quality Gate.

## Principios de seguridad

- No almacenar secretos en Git.
- Usar secretos aleatorios y robustos en producción.
- Mantener separación entre sesiones TENANT y SUPER.
- Aplicar MFA al acceso SUPER.
- Usar Argon2 para passwords.
- Cifrar secretos MFA en reposo.
- Mantener RLS activo para aislamiento de tenants.
- Aplicar permisos RBAC en cada operación protegida.
- Limitar intentos en endpoints sensibles.
- No confiar directamente en headers de proxy para identificar al cliente.
- No registrar credenciales, tokens ni secretos.
- Revisar Quality Gate antes de integrar cambios en `master`.

## Autor

Sebastian Buitrago Betancur — sebastianbbe@gmail.com
