from ..models import UserDB

class UserRepository:
    def __init__(self, db):
        self.db = db

    def add(self, user: UserDB):
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_all(self, status: bool | None = None):
        query = self.db.query(UserDB)
        if status is not None:
            query = query.filter(UserDB.status == status)
        return query.all()

    def get_by_id(self, user_id: int):
        return self.db.query(UserDB).filter(UserDB.id == user_id).first()

    def get_by_dni(self, dni: str):
        return self.db.query(UserDB).filter(UserDB.dni == dni).first()


    def update(self, user: UserDB):
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: UserDB):
        self.db.delete(user)
        self.db.commit()
