from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import ClientDB


class ClientRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, client: ClientDB) -> ClientDB:
        self.db.add(client)
        self.db.flush()
        return client

    def get_all_by_tenant(
        self,
        tenant_id: int,
        include_inactive: bool = False,
    ) -> list[ClientDB]:
        query = self.db.query(ClientDB).filter(ClientDB.tenant_id == tenant_id)
        if not include_inactive:
            query = query.filter(ClientDB.status == "ACTIVE")
        return query.order_by(ClientDB.full_name.asc().nullslast(), ClientDB.uuid.asc()).all()

    def search_by_tenant(
        self,
        tenant_id: int,
        search: str,
        limit: int = 20,
    ) -> list[ClientDB]:
        text = search.strip()
        query = self.db.query(ClientDB).filter(
            ClientDB.tenant_id == tenant_id,
            ClientDB.status == "ACTIVE",
        )
        if text:
            pattern = f"%{text}%"
            query = query.filter(
                or_(
                    ClientDB.id_number.ilike(pattern),
                    ClientDB.full_name.ilike(pattern),
                    ClientDB.email.ilike(pattern),
                    ClientDB.phone.ilike(pattern),
                )
            )
        return query.order_by(ClientDB.full_name.asc().nullslast()).limit(limit).all()

    def get_by_uuid_and_tenant(
        self,
        client_uuid,
        tenant_id: int,
        include_inactive: bool = False,
    ) -> ClientDB | None:
        query = self.db.query(ClientDB).filter(
            ClientDB.uuid == client_uuid,
            ClientDB.tenant_id == tenant_id,
        )
        if not include_inactive:
            query = query.filter(ClientDB.status == "ACTIVE")
        return query.first()

    def get_by_identification_and_tenant(
        self,
        id_type: str,
        id_number: str,
        tenant_id: int,
    ) -> ClientDB | None:
        return self.db.query(ClientDB).filter(
            ClientDB.tenant_id == tenant_id,
            ClientDB.id_type == id_type,
            ClientDB.id_number == id_number,
        ).first()

    def update(self, client: ClientDB) -> ClientDB:
        self.db.add(client)
        self.db.flush()
        return client
