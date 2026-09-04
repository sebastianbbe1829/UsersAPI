from sqlalchemy.orm import Session

from ..models import UserTenantDB


class UserTenantRepository:

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # CREAR
    # ============================================================

    def add(
        self,
        user_tenant: UserTenantDB,
    ) -> UserTenantDB:

        self.db.add(user_tenant)
        self.db.flush()

        return user_tenant

    # Alias explícito para dejar claro que NO hace commit
    def add_without_commit(
        self,
        user_tenant: UserTenantDB,
    ) -> UserTenantDB:

        self.db.add(user_tenant)
        self.db.flush()

        return user_tenant

    # ============================================================
    # BUSCAR POR ID
    #
    # Solo asociaciones no eliminadas.
    # ============================================================

    def get_by_id(
        self,
        user_tenant_id: int,
    ) -> UserTenantDB | None:

        return (
            self.db.query(UserTenantDB)
            .filter(
                UserTenantDB.id == user_tenant_id,
                UserTenantDB.status != 3,
            )
            .first()
        )

    # ============================================================
    # BUSCAR POR ID INCLUYENDO ELIMINADOS
    # ============================================================

    def get_by_id_including_deleted(
        self,
        user_tenant_id: int,
    ) -> UserTenantDB | None:

        return (
            self.db.query(UserTenantDB)
            .filter(
                UserTenantDB.id == user_tenant_id,
            )
            .first()
        )

    # ============================================================
    # BUSCAR USUARIO + TENANT
    #
    # Solo asociaciones activas/inactivas.
    # ============================================================

    def get_by_user_and_tenant(
        self,
        user_id: int,
        tenant_id: int,
    ) -> UserTenantDB | None:

        return (
            self.db.query(UserTenantDB)
            .filter(
                UserTenantDB.user_id == user_id,
                UserTenantDB.tenant_id == tenant_id,
                UserTenantDB.status != 3,
            )
            .first()
        )

    # ============================================================
    # BUSCAR USUARIO + TENANT
    #
    # Incluyendo eliminados.
    #
    # Necesario para poder REACTIVAR una asociación.
    # ============================================================

    def get_by_user_and_tenant_including_deleted(
        self,
        user_id: int,
        tenant_id: int,
    ) -> UserTenantDB | None:

        return (
            self.db.query(UserTenantDB)
            .filter(
                UserTenantDB.user_id == user_id,
                UserTenantDB.tenant_id == tenant_id,
            )
            .first()
        )

    # ============================================================
    # BUSCAR POR ACTIVATION TOKEN
    # ============================================================

    def get_by_activation_token(
        self,
        token: str,
    ) -> UserTenantDB | None:

        return (
            self.db.query(UserTenantDB)
            .filter(
                UserTenantDB.activation_token == token,
            )
            .first()
        )

    # ============================================================
    # BUSCAR TODOS LOS TENANTS DE UN USUARIO
    # ============================================================

    def get_by_user(
        self,
        user_id: int,
    ) -> list[UserTenantDB]:

        return (
            self.db.query(UserTenantDB)
            .filter(
                UserTenantDB.user_id == user_id,
                UserTenantDB.status != 3,
            )
            .all()
        )

    # ============================================================
    # BUSCAR TODOS LOS USUARIOS DE UN TENANT
    # ============================================================

    def get_by_tenant(
        self,
        tenant_id: int,
    ) -> list[UserTenantDB]:

        return (
            self.db.query(UserTenantDB)
            .filter(
                UserTenantDB.tenant_id == tenant_id,
                UserTenantDB.status != 3,
            )
            .all()
        )

    # ============================================================
    # ACTUALIZAR
    # ============================================================

    def update(
        self,
        user_tenant: UserTenantDB,
    ) -> UserTenantDB:

        self.db.add(user_tenant)
        self.db.flush()

        return user_tenant

    # ============================================================
    # MARCAR DIRTY
    # ============================================================

    def mark_dirty(
        self,
        user_tenant: UserTenantDB,
    ) -> UserTenantDB:

        self.db.add(user_tenant)
        self.db.flush()

        return user_tenant

    # ============================================================
    # ELIMINACIÓN LÓGICA
    # ============================================================

    def delete(
        self,
        user_tenant: UserTenantDB,
    ) -> UserTenantDB:

        user_tenant.status = 3

        self.db.add(user_tenant)
        self.db.flush()

        return user_tenant