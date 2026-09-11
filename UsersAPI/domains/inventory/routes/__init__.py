from .inventory_routes import inventory_routes
from .movement_lookup_routes import movement_lookup_routes

inventory_routes.include_router(movement_lookup_routes)

__all__ = ["inventory_routes", "movement_lookup_routes"]
