from .cash_day_routes import cash_day_routes
from .cash_routes import cash_routes

cash_routes.include_router(cash_day_routes)

__all__ = ["cash_routes", "cash_day_routes"]
