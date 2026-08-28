from ..models import TenantConfigDB


class TenantConfigRepository:

    def __init__(self, db):
        self.db = db

    def get_by_tenant_id(self, tenant_id: int):
        return (
            self.db.query(TenantConfigDB)
            .filter(TenantConfigDB.tenant_id == tenant_id)
            .first()
        )

    def add(self, config: TenantConfigDB):
        self.db.add(config)
        self.db.flush()
        self.db.refresh(config)
        return config

    def update(self, config: TenantConfigDB):
        self.db.flush()
        self.db.refresh(config)
        return config
