from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..controllers.bootstrap_controller import bootstrap_application
from ..database import get_db
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
    db: Session = Depends(get_db),
):
    return bootstrap_application(
        datos=datos,
        db=db,
    )