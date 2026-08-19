from ..models import UserDB


class UserRepository:

    def __init__(self, db):
        self.db = db

    def add(self, user: UserDB):

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def get_all(self, status_filter: int | None = None):

        query = self.db.query(UserDB).filter(
            UserDB.status != 3
        )

        if status_filter is not None:
            query = query.filter(
                UserDB.status == status_filter
            )

        return query.all()

    def get_by_id(self, user_id: int):

        return (
            self.db.query(UserDB)
            .filter(
                UserDB.id == user_id,
                UserDB.status != 3,
            )
            .first()
        )

    def get_by_id_including_deleted(self, user_id: int):
        return (
            self.db.query(UserDB)
            .filter(
            UserDB.id == user_id
                ).first()
        )

    def get_by_dni(self, dni: str):

        return (
            self.db.query(UserDB)
            .filter(
                UserDB.dni == dni,
                UserDB.status != 3,
            )
            .first()
        )

    def get_by_email_or_dni(
        self,
        email: str,
        dni: str,
    ):

        # Incluye eliminados para poder reactivarlos
        return (
            self.db.query(UserDB)
            .filter(
                (UserDB.email == email)
                | (UserDB.dni == dni)
            )
            .first()
        )

    def update(self, user: UserDB):

        self.db.commit()
        self.db.refresh(user)

        return user

    def delete(self, user: UserDB):

        # Soft delete
        self.db.query(UserDB).filter(
            UserDB.id == user.id
        ).update({
            UserDB.status: 3
        })

        self.db.commit()
        self.db.refresh(user)

        return user