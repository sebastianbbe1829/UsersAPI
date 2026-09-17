"""Compatibilidad para el caso de uso POS de ventas."""

from ....application.pos_integrations import (
    get_pos_catalog,
    get_pos_client_credit,
    search_pos_clients,
)

__all__ = [
    "get_pos_catalog",
    "get_pos_client_credit",
    "search_pos_clients",
]
