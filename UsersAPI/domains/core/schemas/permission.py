from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ============================================================
# CREAR PERMISO
# ============================================================

class PermissionCreate(BaseModel):

    code: str
    name: str
    description: str | None = None


# ============================================================
# RESPUESTA COMPLETA
# ============================================================

class PermissionRead(BaseModel):

    id: int
    code: str
    name: str
    description: str | None
    status: int
    created_at: datetime
    created_by: str

    model_config = ConfigDict(
        from_attributes=True
    )


# ============================================================
# RESPUESTA PARA CONSULTAS
# ============================================================

class PermissionResponse(BaseModel):

    id: int
    code: str
    name: str
    status: int