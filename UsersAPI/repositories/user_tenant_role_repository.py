from ..models import UserTenantRoleDB


class UserTenantRoleRepository:

    def __init__(self, db):
        self.db = db

    def add(self, user_tenant_role: UserTenantRoleDB):

        self.db.add(user_tenant_role)
        self.db.commit()
        self.db.refresh(user_tenant_role)

        return user_tenant_role

    def get_by_id(
        self,
        user_tenant_role_id: int,
    ):

        return (
            self.db.query(UserTenantRoleDB)
            .filter(
                UserTenantRoleDB.id == user_tenant_role_id,
            )
            .first()
        )

    def get_by_user_tenant_and_role(
        self,
        user_tenant_id: int,
        role_id: int,
    ):

        return (
            self.db.query(UserTenantRoleDB)
            .filter(
                UserTenantRoleDB.user_tenant_id == user_tenant_id,
                UserTenantRoleDB.role_id == role_id,
            )
            .first()
        )

    def get_all_by_user_tenant(
        self,
        user_tenant_id: int,
    ):

        return (
            self.db.query(UserTenantRoleDB)
            .filter(
                UserTenantRoleDB.user_tenant_id == user_tenant_id,
            )
            .all()
        )

    def delete(
        self,
        user_tenant_role: UserTenantRoleDB,
    ):

        self.db.delete(user_tenant_role)
        self.db.commit()

        return user_tenant_role