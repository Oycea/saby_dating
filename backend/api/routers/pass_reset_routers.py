import smtplib
from email.mime.text import MIMEText
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os


from config import SMTP_SERVER, SMTP_PORT, SMTP_PASSWORD, SMTP_USER
from utils import create_reset_password_token, verify_reset_password_token, is_registrated, change_password

router = APIRouter(tags=['Password reset'])

current_file_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_path, '..', '..', '..'))
template_dir = os.path.join(project_root, 'frontend')

templates = Jinja2Templates(directory=template_dir)

# Параметры для отправки письма
subject = 'password reset'
from_email = 'datesaby@gmail.com'


@router.get("/reset_password_form/", response_class=HTMLResponse)
async def reset_password_form_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/reset_password/{token}", response_class=HTMLResponse)
async def reset_password_form(request: Request, token: str):
    email = verify_reset_password_token(token)
    if email is None:
        raise HTTPException(status_code=400, detail="Invalid token")
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})


@router.post("/reset_password/")
async def reset_password(request: Request, email: str = Form(...)):
    print(SMTP_PASSWORD,SMTP_SERVER,SMTP_PORT,SMTP_USER)
    if is_registrated(email):
        token = create_reset_password_token(email)
        reset_password_url = f"http://127.0.0.1:8000/reset_password/{token}"
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
            raise HTTPException(status_code=400, detail=f"Authentication error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"An error occurred: {str(e)}")
        return templates.TemplateResponse("reset_sent.html", {"request": request})
    raise HTTPException(status_code=404, detail="You are not in the database")


@router.post("/reset_password/{token}")
async def process_reset_password(request: Request, token: str, password: str = Form(...),
                                 confirm_password: str = Form(...)):
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    email = verify_reset_password_token(token)
    change_password(email, password)
    if email is None:
        raise HTTPException(status_code=400, detail="Invalid token")
    return templates.TemplateResponse("password_resseted.html", {"request": request})
