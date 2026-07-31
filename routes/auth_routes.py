from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..controllers import auth_controller
from ..database import get_db

auth_routers = APIRouter(prefix="/auth", tags=["Auth"])

@auth_routers.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return auth_controller.login_user(form_data, db)

@auth_routers.get("/validate")
def validate(token: str = Depends(auth_controller.oauth2_scheme), db: Session = Depends(get_db)):
    return auth_controller.validate_token(token, db)
