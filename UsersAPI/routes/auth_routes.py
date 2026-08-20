from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..controllers import auth_controller
from ..database import get_db
from ..schemas import LoginRequest


auth_routers = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@auth_routers.post("/login")
def login(
    datos: LoginRequest,
    db: Session = Depends(get_db),
):

    return auth_controller.login_user(
        datos,
        db,
    )


@auth_routers.get("/validate")
def validate(
    token: str = Depends(auth_controller.oauth2_scheme),
    db: Session = Depends(get_db),
):

    return auth_controller.validate_token(
        token,
        db,
    )