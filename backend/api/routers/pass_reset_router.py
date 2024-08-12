from pydantic import BaseModel
from fastapi import HTTPException, APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from utils import (verify_reset_password_token, is_registrated, change_password,
                   send_message_pass_reset)
from routers.authorization_router import get_current_user, User

pass_reset_router = APIRouter(tags=['Password reset'])


class PasswordResetRequest(BaseModel):
    password: str
    confirm_password: str


@pass_reset_router.get("/validate_token/{token}", name='Проверка токена')
async def validate_token(token: str):
    email = verify_reset_password_token(token)
    if email is None:
        return JSONResponse(status_code=400, content={"detail": "Invalid token"})
    return {"email": email}


@pass_reset_router.post("/reset_password_by_email/{email}", name='Отправить ссылку для смены пароля на почту')
async def reset_password(email: str):
    if is_registrated(email):
        token = send_message_pass_reset(email)
        return token
    raise HTTPException(status_code=404, detail="Вас нет в базе данных")


@pass_reset_router.post("/reset_password/{token}", name='Изменить пароль')
async def process_reset_password(
        token: str,
        password_reset: PasswordResetRequest = Body(...),
):
    password = password_reset.password
    confirm_password = password_reset.confirm_password

    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Пароли не совпадают")

    email = verify_reset_password_token(token)
    if email is None:
        raise HTTPException(status_code=400, detail="Invalid token")
    change_password(email, password)
    return {"Пароль успешно изменен"}


@pass_reset_router.post("/reset_password_loginned/", name='Изменить пароль')
async def process_reset_password(
        current_user: User = Depends(get_current_user),
        password_reset: PasswordResetRequest = Body(...),
):
    password = password_reset.password
    confirm_password = password_reset.confirm_password
    email = current_user.email
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Пароли не совпадают")
    change_password(email, password)
    return {"Пароль успешно изменен"}
