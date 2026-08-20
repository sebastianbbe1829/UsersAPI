from sqlalchemy.orm import Session

from ..models import UserDB, UserTenantDB


class UserRepository:

    def __init__(self, db):
        self.db = db

    def add(
        self,
        user: UserDB
    ):
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def get_all(self):

        return (
            self.db.query(UserDB)
            .all()
        )

    def get_by_dni(self, dni: str):
        return (
            self.db.query(UserDB)
            .filter(UserDB.dni == dni)
            .first()
        )

    def get_all_by_tenant(self, tenant_id: int, status_filter: int | None = None):
        query = (
            self.db.query(UserDB)
            .join(UserTenantDB, UserTenantDB.user_id == UserDB.id)
            .filter(
                UserTenantDB.tenant_id == tenant_id,
                UserTenantDB.status != 3,
            )
        )
        if status_filter is not None:
            query = query.filter(UserTenantDB.status == status_filter)
        return query.all()

    def get_by_id(
        self,
        db: Session,
        id_user: int,
    ):
        return (
            self.db.query(UserDB)
            .filter(
                UserDB.id == id_user
            )
            .first()
        )

    def get_by_id_including_deleted(
        self,
        id_user: int
    ):
        return (
            self.db.query(UserDB)
            .filter(
                UserDB.id == id_user
            )
            .first()
        )
