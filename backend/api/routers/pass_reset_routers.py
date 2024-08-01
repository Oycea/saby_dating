import smtplib
from email.mime.text import MIMEText
from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config import SMTP_SERVER, SMTP_PORT, SMTP_PASSWORD, SMTP_USER
from routers.session import open_conn
from utils import create_reset_password_token, verify_reset_password_token, is_registrated, change_password

router = APIRouter(tags=['Password reset'])
templates = Jinja2Templates(directory="/frontend/")

# Параметры для отправки письма
subject = 'password reset'
from_email = 'datesaby@gmail.com'


@router.get("/reset-password-form/", response_class=HTMLResponse)
async def reset_password_form_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/reset-password/")
async def reset_password(email: str = Form(...)):
    if is_registrated(email):
        token = create_reset_password_token(email)
        reset_password_url = f"http://127.0.0.1:8000/reset-password/{token}"
        print(reset_password_url)
        body = f"Ссылка для сброса пароля: {reset_password_url}"
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = email

        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        except smtplib.SMTPAuthenticationError as e:
            raise HTTPException(status_code=400)
        except Exception as e:
            raise HTTPException(status_code=400)
        return {"message": "Instructions to reset your password have been sent to your email."}
    raise HTTPException(status_code=404, detail="U r not in base")


@router.get("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_form(request: Request, token: str):
    email = verify_reset_password_token(token)
    if email is None:
        raise HTTPException(status_code=400, detail="Invalid token")
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})


@router.post("/reset-password/{token}")
async def process_reset_password(token: str, password: str = Form(...), confirm_password: str = Form(...)):
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    email = verify_reset_password_token(token)
    change_password(email, password)
    if email is None:
        raise HTTPException(status_code=400, detail="Invalid token")
    return {"message": "Password has been reset successfully."}
