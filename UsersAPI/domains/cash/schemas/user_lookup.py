from pydantic import BaseModel


class CashAssignableUserRead(BaseModel):
    id: int
    name: str
    dni: str
