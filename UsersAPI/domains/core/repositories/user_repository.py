from sqlalchemy.orm import Session

from ..models import UserDB, UserTenantDB


class UserRepository:

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # CREAR
    # ============================================================

    def add(
        self,
        user: UserDB,
    ) -> UserDB:
        """
        Agrega un usuario a la sesión y ejecuta flush.

        NO hace commit.

        El commit/rollback de la transacción completa
        es responsabilidad de la capa transaccional superior.
        """

        self.db.add(user)
        self.db.flush()

        return user

    # ============================================================
    # CONSULTAR TODOS
    # ============================================================

    def get_all(self) -> list[UserDB]:

        return (
            self.db.query(UserDB)
            .all()
        )

    # ============================================================
    # BUSCAR POR DNI
    # ============================================================

    def get_by_dni(
        self,
        dni: str,
    ) -> UserDB | None:

        return (
            self.db.query(UserDB)
            .filter(
                UserDB.dni == dni,
            )
            .first()
        )

    # ============================================================
    # BUSCAR POR ID
    # ============================================================

    def get_by_id(
        self,
        user_id: int,
    ) -> UserDB | None:

        return (
            self.db.query(UserDB)
            .filter(
                UserDB.id == user_id,
            )
            .first()
        )

    # ============================================================
    # BUSCAR POR DNI + TENANT
    # ============================================================

    def get_by_dni_in_tenant(
        self,
        dni: str,
        tenant_id: int,
    ) -> UserDB | None:

        return (
            self.db.query(UserDB)
            .join(
                UserTenantDB,
                UserTenantDB.user_id == UserDB.id,
            )
            .filter(
                UserDB.dni == dni,
                UserTenantDB.tenant_id == tenant_id,
                UserTenantDB.status != 3,
            )
            .first()
        )

    # ============================================================
    # BUSCAR POR ID + TENANT
    # ============================================================

    def get_by_id_and_tenant(
        self,
        user_id: int,
        tenant_id: int,
    ) -> UserDB | None:

        return (
            self.db.query(UserDB)
            .join(
                UserTenantDB,
                UserTenantDB.user_id == UserDB.id,
            )
            .filter(
                UserDB.id == user_id,
                UserTenantDB.tenant_id == tenant_id,
                UserTenantDB.status != 3,
            )
            .first()
        )

    # ============================================================
    # LISTAR POR TENANT
    # ============================================================

    def get_all_by_tenant(
        self,
        tenant_id: int,
        status_filter: int | None = None,
    ) -> list[UserDB]:

        query = (
            self.db.query(UserDB)
            .join(
                UserTenantDB,
                UserTenantDB.user_id == UserDB.id,
            )
            .filter(
                UserTenantDB.tenant_id == tenant_id,
                UserTenantDB.status != 3,
            )
        )

        if status_filter is not None:
            query = query.filter(
                UserTenantDB.status == status_filter
            )

        return query.all()

    # ============================================================
    # BUSCAR INCLUYENDO ELIMINADOS
    # ============================================================

    def get_by_id_including_deleted(
        self,
        user_id: int,
    ) -> UserDB | None:

        return (
            self.db.query(UserDB)
            .filter(
                UserDB.id == user_id,
            )
            .first()
        )

    # ============================================================
    # ACTUALIZAR / MARCAR CAMBIOS
    # ============================================================

    def update(
        self,
        user: UserDB,
    ) -> UserDB:
        """
        Sincroniza los cambios de UserDB con la sesión.

        NO hace commit.
        """

        self.db.add(user)
        self.db.flush()

        return user