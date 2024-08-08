import os
import logging

from jose import JWTError, jwt
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from fastapi import HTTPException
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import (SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
                    SMTP_SERVER, SMTP_PORT, SMTP_PASSWORD, SMTP_USER)
from routers.session import open_conn
from routers.authorization_router import get_password_hash, check_password


def create_reset_password_token(email: str):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": email}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_reset_password_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise JWTError
        return email
    except JWTError:
        return None


def is_registrated(email: str):
    with open_conn() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            if not user:
                return False
            return True


def change_password(email: str, password: str):
    with open_conn() as connection:
        with connection.cursor() as cursor:
            check_password(password)
            hashed_password = get_password_hash(password)
            cursor.execute("""UPDATE users SET password = %s WHERE email = %s""", (hashed_password, email))
            connection.commit()


def send_message(email: str):
    token = create_reset_password_token(email)
    reset_password_url = f"http://195.133.201.168:8000/password_reset.html/{token}"
    body_text = f"Ссылка для сброса пароля: {reset_password_url}"
    body_html = f"""
       <html>
           <body>
               <p>Ссылка для сброса пароля:<br>
                  <a href="{reset_password_url}">{reset_password_url}</a>
               </p>
           </body>
       </html>
       """

    # Создание сообщения
    msg = MIMEMultipart('alternative')
    msg['From'] = SMTP_USER
    msg['To'] = email
    msg['Subject'] = 'Password reset'
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid()

    # Добавление тела сообщения
    msg.attach(MIMEText(body_text, 'plain'))
    msg.attach(MIMEText(body_html, 'html'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.connect(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise HTTPException(status_code=400, detail=f"Authentication error: {str(e)}")
    except smtplib.SMTPException as e:
        raise HTTPException(status_code=500, detail=f"SMTP error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    return token


def setup_logging():
    # Определение пути к директории проекта
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    log_directory = os.path.join(base_dir, 'logs')
    log_file_path = os.path.join(log_directory, 'app.log')

    # Создание директории, если она не существует
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # Настройка логгера
    logging.basicConfig(
        filename=log_file_path,
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    return logger


def clear_logs(log_directory=None):
    if log_directory is None:
        # Определение пути к директории проекта
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        log_directory = os.path.join(base_dir, 'logs')

    if not os.path.exists(log_directory):
        logging.error(f"Log directory {log_directory} does not exist.")
        return

    for filename in os.listdir(log_directory):
        file_path = os.path.join(log_directory, filename)
        if os.path.isfile(file_path):
            with open(file_path, 'w'):
                pass
    logging.info("Logs have been cleared.")


def setup_scheduler(log_directory=None):
    if log_directory is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        log_directory = os.path.join(base_dir, 'logs')

    scheduler = BackgroundScheduler()
    scheduler.start()

    scheduler.add_job(
        clear_logs,
        trigger=IntervalTrigger(hours=24),
        args=[log_directory],
        replace_existing=True
    )
    return scheduler
