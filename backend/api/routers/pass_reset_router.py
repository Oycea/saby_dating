import os

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from utils import create_reset_password_token, verify_reset_password_token, is_registrated, change_password, \
    send_message

pass_reset_router = APIRouter(tags=['Password reset'])

current_file_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_path, '..', '..', '..'))
template_dir = os.path.join(project_root, 'frontend/templates')

templates = Jinja2Templates(directory=template_dir)


@pass_reset_router.get("/reset_password/{token}", response_class=HTMLResponse, name="страница для смены пароля")
async def reset_password_form(request: Request, token: str):
    return templates.TemplateResponse("password_reset.html", {"request": request, "token": token})


@pass_reset_router.post("/reset_password/", name='Отправить ссылку для смены пароля на почту')
async def reset_password(email: str = Form(...)):
    if is_registrated(email):
        token = send_message(email)
        return token
    raise HTTPException(status_code=404, detail="Вас нет в базе данных")  # Перевести на регистрацию


@pass_reset_router.post("/reset_password/{token}", name='Изменить пароль')
async def process_reset_password(token: str, password: str = Form(...),
                                 confirm_password: str = Form(...)):
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Пароли не совпадают")
    email = verify_reset_password_token(token)
    change_password(email, password)
    if email is None:
        raise HTTPException(status_code=400, detail="Invalid token")
    return {"message": "Пароль успешно изменен"}
