# UsersAPI

API REST multi-tenant construida con FastAPI, SQLAlchemy y PostgreSQL. Provee gestión de usuarios, tenants (empresas), roles y permisos (RBAC), autenticación JWT, un rol administrativo global (SUPER) con MFA, y un módulo de negocio para inventario y control de extintores.

## Características principales

- **Multi-tenancy real**: aislamiento de datos entre tenants usando Row-Level Security (RLS) de PostgreSQL, no solo filtros en la aplicación.
- **RBAC (roles y permisos)**: los usuarios se autentican solo si tienen un rol con el permiso `AUTHENTICATE`; cada acción protegida valida permisos específicos (`USER_CREATE`, `TENANT_UPDATE`, etc.).
- **Autenticación JWT** con expiración configurable y passwords cifrados con Argon2.
- **Usuario SUPER**: identidad global con MFA por TOTP (compatible con Google Authenticator), secretos cifrados en reposo con Fernet.
- **Recuperación de contraseña y activación de cuenta** mediante códigos OTP con expiración y límite de intentos.
- **Módulo de extintores**: inventario, catálogo de tipos, ciclo de inspecciones, control de pruebas hidrostáticas y notificaciones automáticas de recarga por email/WhatsApp.
- **Exportación a Excel** de usuarios y extintores.
- CI en GitHub Actions con Postgres real, migraciones Alembic y escaneo de seguridad con `bandit`.

## Arquitectura

El código sigue una separación en capas:

```
routes/        → definición de endpoints HTTP, validación de permisos
controllers/   → orquestación entre routes y services
services/      → lógica de negocio
repositories/  → acceso a datos (SQLAlchemy)
models/        → modelos ORM
schemas/       → esquemas Pydantic (request/response)
security/      → dependencias de autenticación y RBAC
util/          → utilidades (Excel, email, WhatsApp)
```

## Requisitos

- Python 3.12+
- PostgreSQL 16+ (con soporte para Row-Level Security)
- pip

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\\Scripts\\activate     # Windows
pip install -r requirements.txt
```

## Variables de entorno

Crea un archivo `.env` en la raíz del proyecto. Variables principales:

```
# JWT
SECRET_KEY=<clave aleatoria larga, ej. secrets.token_urlsafe(64)>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15

# Base de datos
DATABASE_URL=postgresql+psycopg://usuario:password@host:5432/db
BOOTSTRAP_DATABASE_URL=postgresql+psycopg://usuario_bootstrap:password@host:5432/db
DATABASE_ADMIN_URL=postgresql+psycopg://admin:password@host:5432/db

# Bootstrap de tenants
BOOTSTRAP_TENANT_KEY=<clave para inicializar tenants>

# Usuario SUPER
SUPER_BOOTSTRAP_SECRET=<clave para crear el usuario SUPER>
SUPER_MFA_ENCRYPTION_KEY=<clave Fernet para cifrar secretos MFA>

# Email (Brevo/Resend)
BREVO_API_KEY=<api key>
EMAIL_FROM=<email remitente>
EMAIL_FROM_NAME=UsersAPI
EMAIL_KEY=<clave interna de validación>
FRONTEND_URL=<url del frontend>
BACKEND_URL=<url pública de este backend>
API_EMAIL_URL=<endpoint de envío de email, si aplica>

# OTP
OTP_API_KEY=<clave interna>
OTP_LENGTH=6
OTP_EXPIRE_MINUTES=10
OTP_MAX_ATTEMPTS=5

# WhatsApp Cloud API
WHATSAPP_TOKEN=<token>
WHATSAPP_PHONE_ID=<id del número>
WHATSAPP_MODE=template
WHATSAPP_API_URL=<url de la API>

# Job de notificaciones de recarga de extintores
EXTINGUISHER_RECHARGE_NOTIFICATIONS_ENABLED=true
EXTINGUISHER_RECHARGE_NOTIFICATION_TIME=08:00
JOB_TIMEZONE=America/Bogota
```

> **Importante:** `SECRET_KEY`, `SUPER_BOOTSTRAP_SECRET` y `SUPER_MFA_ENCRYPTION_KEY` deben ser valores aleatorios y robustos en cualquier entorno que no sea desarrollo local.

## Migraciones de base de datos

El proyecto usa Alembic. Para aplicar migraciones:

```bash
alembic upgrade head
```

## Ejecutar la API

```bash
uvicorn UsersAPI.main:app --reload
```

Documentación interactiva disponible en:

- <http://127.0.0.1:8000/docs> (Swagger)
- <http://127.0.0.1:8000/redoc>

## Probar la API

```bash
pytest -q
```

El proyecto cuenta con más de 90 pruebas, incluyendo suites dedicadas a aislamiento multi-tenant, políticas RLS, autenticación del usuario SUPER y protección contra fuerza bruta (`test/security/`).

## Rate limiting

Los endpoints sensibles de autenticación, MFA, recuperación de contraseña y bootstrap SUPER utilizan un rate limiter de ventanas deslizantes en memoria. Las restricciones combinan identificadores por IP y por cuenta cuando corresponde, y los bloqueos responden con HTTP `429` y `Retry-After`.

En la configuración actual de producción, la API se ejecuta como una instancia del servicio Web en Render, por lo que el almacenamiento en memoria es suficiente para mantener el contador coherente dentro de esa instancia. El limiter no confía directamente en `X-Forwarded-For` ni `X-Real-IP`; utiliza `request.client.host` hasta que exista una cadena de proxies confiables explícitamente configurada y validada.

**Escalamiento horizontal:** si la API pasa a ejecutarse en múltiples instancias/procesos independientes, cada instancia tendría su propio contador. En ese escenario, el rate limiter debe migrarse a un almacenamiento compartido, por ejemplo Redis, para conservar límites consistentes entre instancias.

## Endpoints principales

### Usuarios
- `POST /users` — crear usuario
- `GET /users` — listar usuarios
- `GET /users/export` — exportar usuarios a Excel
- `GET /users/{dni}` — obtener usuario por DNI
- `PATCH /users/{dni}` — actualizar usuario
- `DELETE /users/{dni}` — eliminar usuario

### Autenticación
- `POST /auth/login` — iniciar sesión y obtener token JWT
- `GET /auth/validate` — validar token

### Autenticación SUPER (global, con MFA)
- Endpoints de bootstrap, login y verificación MFA para el usuario administrativo global

### Recuperación de contraseña y OTP
- Endpoints para solicitar y validar códigos OTP de recuperación y activación de cuenta

### Tenants
- CRUD completo de tenants, configuración de UI por tenant

### Roles y permisos
- CRUD de roles, permisos, y asociación de permisos a roles
- Asociación de roles a usuarios por tenant (`user_tenant_role`)

### Extintores
- CRUD de extintores, tipos de extintor, inspecciones e ítems de inspección
- `GET /extinguishers/export` — exportar extintores a Excel
- `GET /extinguishers/search` — búsqueda de extintores

## Seguridad

- Passwords con hash Argon2.
- Comparación de secretos sensibles con `hmac.compare_digest` para evitar timing attacks.
- Secretos MFA cifrados en reposo con Fernet.
- Aislamiento de datos por tenant mediante RLS a nivel de PostgreSQL.
- Rate limiting para endpoints sensibles de autenticación, recuperación, MFA y bootstrap.
- Escaneo estático de seguridad con `bandit` en cada ejecución de CI.

## Autor

Sebastian Buitrago Betancur — sebastianbbe@gmail.com
