import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..controllers.bootstrap_controller import bootstrap_application
from ..database import get_bootstrap_db
from ..schemas import BootstrapRequest, BootstrapResponse


bootstrap_routes = APIRouter(
    prefix="/bootstrap",
    tags=["Bootstrap"],
)


@bootstrap_routes.post(
    "",
    response_model=BootstrapResponse,
    status_code=status.HTTP_201_CREATED,
)
def bootstrap_route(
    datos: BootstrapRequest,
    x_bootstrap_key: str = Header(..., alias="X-Bootstrap-Key"),
    db: Session = Depends(get_bootstrap_db),
):
    """Provisiona una nueva empresa mediante una clave interna.

    Bootstrap no utiliza JWT ni tenant porque su función es precisamente
    crear el tenant y su contexto administrativo inicial. La autorización
    del proceso se realiza mediante una clave secreta almacenada en
    BOOTSTRAP_KEY.
    """

    bootstrap_key = os.getenv("BOOTSTRAP_KEY")

    if not bootstrap_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="BOOTSTRAP_KEY no está configurada.",
        )

    if not secrets.compare_digest(x_bootstrap_key, bootstrap_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clave de bootstrap inválida.",
        )

    return bootstrap_application(
        datos=datos,
        db=db,
    )
