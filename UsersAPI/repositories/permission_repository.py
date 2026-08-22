from sqlalchemy.orm import Session

from ..models import PermissionDB


class PermissionRepository:

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # BUSCAR PERMISO ACTIVO POR CÓDIGO
    # ============================================================

    def get_by_code(
        self,
        code: str,
    ) -> PermissionDB | None:

        return (
            self.db.query(PermissionDB)
            .filter(
                PermissionDB.code == code,
                PermissionDB.status == 1,
            )
            .first()
        )

    # ============================================================
    # BUSCAR PERMISO POR CÓDIGO
    #
    # Incluye permisos inactivos.
    # Se utiliza principalmente para validar duplicados.
    # ============================================================

    def get_by_code_any_status(
        self,
        code: str,
    ) -> PermissionDB | None:

        return (
            self.db.query(PermissionDB)
            .filter(
                PermissionDB.code == code,
            )
            .first()
        )

    # ============================================================
    # LISTAR PERMISOS ACTIVOS
    # ============================================================

    def get_all_by_permission(
        self,
    ) -> list[PermissionDB]:

        return (
            self.db.query(PermissionDB)
            .filter(
                PermissionDB.status == 1
            )
            .all()
        )

    # ============================================================
    # CREAR PERMISO
    # ============================================================

    def create(
        self,
        permission: PermissionDB,
    ) -> PermissionDB:

        self.db.add(permission)

        self.db.flush()

        self.db.refresh(permission)

        return permission