# UsersAPI

API REST para gestionar usuarios con FastAPI, SQLAlchemy y autenticación JWT.

## Requisitos

- Python 3.10+
- pip

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

Si aún no tienes el archivo de dependencias, puedes instalar lo mínimo con:

```bash
pip install fastapi uvicorn sqlalchemy python-jose passlib[argon2] python-dotenv pydantic email-validator pytest httpx python-multipart
```

## Variables de entorno

Crea un archivo `.env` basado en `.env.example`:

```env
SECRET_KEY=change-me
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
```

## Ejecutar la API

```bash
uvicorn UsersAPI.main:app --reload
```

La documentación Swagger estará disponible en:

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/redoc

## Probar la API

```bash
pytest -q
```

## Endpoints principales

- POST /users: crear usuario
- GET /users: listar usuarios
- GET /users/{dni}: obtener usuario por DNI
- PATCH /users/{dni}: actualizar usuario
- DELETE /users/{dni}: eliminar usuario
- POST /auth/login: iniciar sesión y obtener token
- GET /auth/validate: validar token
