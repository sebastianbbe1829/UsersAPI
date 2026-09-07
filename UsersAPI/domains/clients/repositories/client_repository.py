from uuid import UUID

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

    def get_all(
        self,
        tenant_id: int,
        limit: int | None = None,
        offset: int = 0,
        search: str | None = None,
    ) -> list[ClientDB]:
        query = self.db.query(ClientDB).filter(ClientDB.tenant_id == tenant_id)

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    ClientDB.identification_number.ilike(term),
                    ClientDB.full_name.ilike(term),
                    ClientDB.email.ilike(term),
                    ClientDB.status.ilike(term),
                    ClientDB.compliance_status.ilike(term),
                    ClientDB.list_type.ilike(term),
                )
            )

        query = query.order_by(ClientDB.full_name, ClientDB.id).offset(max(offset, 0))
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def get_by_id(self, client_id: UUID, tenant_id: int) -> ClientDB | None:
        return (
            self.db.query(ClientDB)
            .filter(
                ClientDB.id == client_id,
                ClientDB.tenant_id == tenant_id,
            )
            .first()
        )

    def get_by_identification(
        self,
        identification_type_id: int,
        identification_number: str,
        tenant_id: int,
    ) -> ClientDB | None:
        return (
            self.db.query(ClientDB)
            .filter(
                ClientDB.tenant_id == tenant_id,
                ClientDB.identification_type_id == identification_type_id,
                ClientDB.identification_number == identification_number,
            )
            .first()
        )

    def update(self, client: ClientDB) -> ClientDB:
        self.db.add(client)
        self.db.flush()
        return client

    def delete(self, client: ClientDB) -> None:
        self.db.delete(client)
        self.db.flush()
