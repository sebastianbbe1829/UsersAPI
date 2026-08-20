from ..models import TenantDB, UserTenantDB


class TenantRepository:

    def __init__(self, db):
        self.db = db

    def add(self, tenant: TenantDB):
        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def get_all(self, status_filter: int | None = None):

        query = self.db.query(TenantDB).filter(
            TenantDB.status != 3
        )

        if status_filter is not None:
            query = query.filter(
                TenantDB.status == status_filter
            )

        return query.all()

    def get_by_id(self, tenant_id: int):

        return (
            self.db.query(TenantDB)
            .filter(
                TenantDB.id == tenant_id,
                TenantDB.status != 3,
            )
            .first()
        )

    def get_by_id_including_deleted(self, tenant_id: int):
        return (
            self.db.query(TenantDB)
            .filter(
            TenantDB.id == tenant_id
                ).first()
            )

    def get_by_slug(self, slug: str):

        return (
            self.db.query(TenantDB)
            .filter(
                TenantDB.slug == slug,
                TenantDB.status != 3,
            )
            .first()
        )

    def get_by_name(self, name: str):

        return (
            self.db.query(TenantDB)
            .filter(
                TenantDB.name == name,
                TenantDB.status != 3,
            )
            .first()
        )

    def update(self, tenant: TenantDB):

        self.db.commit()
        self.db.refresh(tenant)

        return tenant

    def delete(self, tenant: TenantDB):

        self.db.query(TenantDB).filter(
            TenantDB.id == tenant.id
        ).update({
            TenantDB.status: 3
        })

        self.db.commit()
        self.db.refresh(tenant)

        return tenant

    def get_by_user_id(
        self,
        user_id,
        status_filter: int | None = 1,
    ):
        query = (
            self.db.query(TenantDB)
            .join(
                UserTenantDB,
                UserTenantDB.tenant_id == TenantDB.id,
            )
            .filter(
                UserTenantDB.user_id == user_id,
                UserTenantDB.status == 1,
                TenantDB.status != 3,
            )
        )

        if status_filter is not None:
            query = query.filter(
            TenantDB.status == status_filter
            )

        return query.all()