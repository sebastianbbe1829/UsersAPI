from ..models import UserTenantDB, UserDB



class UserTenantRepository:

    def __init__(self, db):
        self.db = db

    def add(self, user_tenant: UserTenantDB):
        self.db.add(user_tenant)
        self.db.commit()
        self.db.refresh(user_tenant)
        return user_tenant

    def get_by_id(self, user_tenant_id: int):
        return (
            self.db.query(UserTenantDB)
            .filter(
                UserTenantDB.id == user_tenant_id,
                UserTenantDB.status != 3,
            )
            .first()
        )

    def get_by_user_and_tenant(
        self,
        user_id: int,
        tenant_id: int,
    ):
        return (
            self.db.query(UserTenantDB)
            .filter(
                UserTenantDB.user_id == user_id,
                UserTenantDB.tenant_id == tenant_id,
                UserTenantDB.status != 3,
            )
            .first()
        )

    def get_by_user(self, user_id: int):
        return (
            self.db.query(UserTenantDB)
            .filter(
                UserTenantDB.user_id == user_id,
                UserTenantDB.status != 3,
            )
            .all()
        )

    def get_by_tenant(self, tenant_id: int):
        return (
            self.db.query(UserTenantDB)
            .filter(
                UserTenantDB.tenant_id == tenant_id,
                UserTenantDB.status != 3,
            )
            .all()
        )

    def update(self, user_tenant: UserTenantDB):
        self.db.commit()
        self.db.refresh(user_tenant)
        return user_tenant

    def delete(self, user_tenant: UserTenantDB):
        self.db.query(UserTenantDB).filter(
            UserTenantDB.id == user_tenant.id
        ).update({
            UserTenantDB.status: 3
        })

        self.db.commit()
        self.db.refresh(user_tenant)

        return user_tenant

