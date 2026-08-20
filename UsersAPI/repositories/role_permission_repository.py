from sqlalchemy.orm import Session

from ..models import RolePermissionDB


class RolePermissionRepository:

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # BUSCAR RELACIÓN ROL - PERMISO
    # ============================================================

    def get_by_role_permission(
        self,
        role_id: int,
        permission_id: int,
    ) -> RolePermissionDB | None:

        return (
            self.db.query(RolePermissionDB)
            .filter(
                RolePermissionDB.role_id == role_id,
                RolePermissionDB.permission_id == permission_id,
            )
            .first()
        )

    # ============================================================
    # AGREGAR RELACIÓN
    # ============================================================

    def add(
        self,
        role_permission: RolePermissionDB,
    ) -> RolePermissionDB:

        self.db.add(role_permission)
        self.db.commit()
        self.db.refresh(role_permission)

        return role_permission

    # ============================================================
    # BUSCAR PERMISOS DE UN ROL
    # ============================================================

    def get_permissions_by_role(
        self,
        role_id: int,
    ) -> list[RolePermissionDB]:

        return (
            self.db.query(RolePermissionDB)
            .filter(
                RolePermissionDB.role_id == role_id,
            )
            .all()
        )

    # ============================================================
    # BUSCAR RELACIÓN POR ID
    # ============================================================

    def get_by_id(
        self,
        role_permission_id: int,
    ) -> RolePermissionDB | None:

        return (
            self.db.query(RolePermissionDB)
            .filter(
                RolePermissionDB.id == role_permission_id,
            )
            .first()
        )

    # ============================================================
    # ELIMINAR RELACIÓN
    # ============================================================

    def delete(
        self,
        role_permission: RolePermissionDB,
    ) -> None:

        self.db.delete(role_permission)
        self.db.commit()