from ..models import RoleDB


class RoleRepository:

    def __init__(self, db):
        self.db = db

    def add(self, role: RoleDB):

        self.db.add(role)
        self.db.flush()
        self.db.refresh(role)

        return role

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

    def update(self, role: RoleDB):

        self.db.flush()
        self.db.refresh(role)
        self.db.flush()
        return role

    def delete(self, role: RoleDB):

        self.db.query(RoleDB).filter(
            RoleDB.id == role.id
        ).update({
            RoleDB.status: 3
        })

        self.db.flush()
        self.db.refresh(role)
        self.db.flush()

        return role