from pydantic import BaseModel

from UsersAPI.domains.inventory.schemas import InventoryRead, ProductRead


class SalesPOSClientRead(BaseModel):
    id: str
    full_name: str
    identification_number: str
    status: str
    email: str | None = None


class SalesPOSCreditRead(BaseModel):
    client_id: str
    approved_limit: float
    credit_used: float
    credit_available: float


class SalesPOSCatalogRead(BaseModel):
    products: list[ProductRead]
    top_products: list[ProductRead]
    inventory: list[InventoryRead]
