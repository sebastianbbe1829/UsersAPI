from ..models import RoleDB


class RoleRepository:

    def __init__(self, db):
        self.db = db

    # ============================================================
    # CREAR
    # ============================================================

    def add(
        self,
        role: RoleDB,
    ):

        self.db.add(role)

        self.db.flush()

        self.db.refresh(role)

        return role


    # ============================================================
    # LISTAR ROLES DEL TENANT
    # ============================================================

    def get_all_by_tenant(
        self,
        tenant_id: int,
        status_filter: int | None = None,
    ):

        query = (
            self.db.query(RoleDB)
            .filter(
                RoleDB.tenant_id == tenant_id,
                RoleDB.status != 3,
            )
        )

        if status_filter is not None:

            query = query.filter(
                RoleDB.status == status_filter
            )

        return query.all()


    # ============================================================
    # BUSCAR POR ID
    # ============================================================

    def get_by_id(
        self,
        role_id: int,
        tenant_id: int,
    ):

        return (
            self.db.query(RoleDB)
            .filter(
                RoleDB.id == role_id,
                RoleDB.tenant_id == tenant_id,
                RoleDB.status != 3,
            )
            .first()
        )


    # ============================================================
    # BUSCAR CÓDIGO ACTIVO
    # ============================================================

    def get_by_code(
        self,
        code: str,
        tenant_id: int,
    ):

        return (
            self.db.query(RoleDB)
            .filter(
                RoleDB.code == code,
                RoleDB.tenant_id == tenant_id,
                RoleDB.status != 3,
            )
            .first()
        )


    # ============================================================
    # BUSCAR CÓDIGO INCLUYENDO ELIMINADOS
    # ============================================================

    def get_by_code_including_deleted(
        self,
        code: str,
        tenant_id: int,
    ):

        return (
            self.db.query(RoleDB)
            .filter(
                RoleDB.code == code,
                RoleDB.tenant_id == tenant_id,
            )
            .first()
        )


    # ============================================================
    # BUSCAR NOMBRE ACTIVO
    # ============================================================

    def get_by_name(
        self,
        name: str,
        tenant_id: int,
    ):

        return (
            self.db.query(RoleDB)
            .filter(
                RoleDB.name == name,
                RoleDB.tenant_id == tenant_id,
                RoleDB.status != 3,
            )
            .first()
        )


    # ============================================================
    # BUSCAR NOMBRE INCLUYENDO ELIMINADOS
    # ============================================================

    def get_by_name_including_deleted(
        self,
        name: str,
        tenant_id: int,
    ):

        return (
            self.db.query(RoleDB)
            .filter(
                RoleDB.name == name,
                RoleDB.tenant_id == tenant_id,
            )
            .first()
        )


    # ============================================================
    # ACTUALIZAR
    # ============================================================

    def update(
        self,
        role: RoleDB,
    ):

        self.db.flush()

        self.db.refresh(role)

        self.db.flush()

        return role


    # ============================================================
    # ELIMINACIÓN LÓGICA
    # ============================================================

    def delete(
        self,
        role: RoleDB,
    ):

        self.db.query(RoleDB).filter(
            RoleDB.id == role.id
        ).update({
            RoleDB.status: 3
        })

        self.db.flush()

        self.db.refresh(role)

        self.db.flush()

        return role