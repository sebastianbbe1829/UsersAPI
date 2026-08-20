from pydantic import BaseModel, ConfigDict


# ============================================================
# ASIGNAR PERMISO A ROL
# ============================================================

class RolePermissionCreate(BaseModel):

    role_id: int
    permission_id: int


# ============================================================
# RESPUESTA
# ============================================================

class RolePermissionRead(BaseModel):

    id: int
    role_id: int
    permission_id: int

    model_config = ConfigDict(
        from_attributes=True,
    )


# ============================================================
# ELIMINAR PERMISO DEL ROL
# ============================================================

class RolePermissionDeleteResponse(BaseModel):

    id: int
    role_id: int
    permission_id: int
    message: str