from sqlalchemy.orm import Session

from ..models import PermissionDB


class PermissionRepository:

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # BUSCAR PERMISO POR CÓDIGO
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