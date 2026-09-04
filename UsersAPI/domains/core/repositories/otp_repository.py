from sqlalchemy.orm import Session

from ..models.otp import OTPCodeDB


class OTPRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active(self, destination: str, purpose: str):
        return (
            self.db.query(OTPCodeDB)
            .filter(
                OTPCodeDB.destination == destination,
                OTPCodeDB.purpose == purpose,
                OTPCodeDB.consumed_at.is_(None),
            )
            .order_by(OTPCodeDB.created_at.desc(), OTPCodeDB.id.desc())
            .first()
        )

    def get_active_all(self, destination: str, purpose: str):
        return (
            self.db.query(OTPCodeDB)
            .filter(
                OTPCodeDB.destination == destination,
                OTPCodeDB.purpose == purpose,
                OTPCodeDB.consumed_at.is_(None),
            )
            .all()
        )

    def add(self, otp: OTPCodeDB) -> OTPCodeDB:
        self.db.add(otp)
        self.db.flush()
        return otp

    def update(self, otp: OTPCodeDB) -> OTPCodeDB:
        self.db.add(otp)
        self.db.flush()
        return otp
