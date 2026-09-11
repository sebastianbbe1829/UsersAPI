from pydantic import BaseModel


class PortfolioPaymentClientRead(BaseModel):
    id: str
    full_name: str
    identification_number: str
    status: str
    email: str | None = None
