import os
import logging
import socket

from jose import JWTError, jwt
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from fastapi import HTTPException, status
from passlib.hash import argon2
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import (SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
                    SMTP_SERVER, SMTP_PORT, SMTP_PASSWORD, SMTP_USER)
from routers.session import open_conn


def create_token(email: str):
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


def check_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароль должен содержать не менее 8 символов"
        )
    if not any(symbol.isalpha() for symbol in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароль должен содержать хотя бы одну букву"
        )
    if not any(symbol.isdigit() for symbol in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароль должен содержать хотя бы одну цифру"
        )


def change_password(email: str, password: str):
    with open_conn() as connection:
        with connection.cursor() as cursor:
            check_password(password)
            hashed_password = argon2.hash(password)
            cursor.execute("""UPDATE users SET password = %s WHERE email = %s""", (hashed_password, email))
            connection.commit()


def send_message(email: str, subject: str, body: str):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise HTTPException(status_code=400, detail=f"Authentication error: {str(e)}")
    except smtplib.SMTPException as e:
        raise HTTPException(status_code=500, detail=f"SMTP error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


def send_message_pass_reset(email: str):
    token = create_token(email)
    reset_password_url = f"http://195.133.201.168:80/change_password.html?{token}"
    body = f"Ссылка для сброса пароля: {reset_password_url}"
    subject = 'Смена пароля'
    send_message(email, subject, body)
    return token


def send_message_email_verification(email: str, token: str):
    confirm_registration_url = f"http://195.133.201.168:80/registration_complete.html?{token}"
    body = f"Ссылка для подтверждения регистрации: {confirm_registration_url}"
    subject = 'Подтверждение регистрации'
    send_message(email, subject, body)


# Определение пути к директории проекта
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
log_directory = os.path.join(base_dir, 'logs')
log_file_path = os.path.join(log_directory, 'app.log')


# логгирование
class IPFilter(logging.Filter):
    def filter(self, record):
        record.ip_address = self.get_ip_address()
        return True

    def get_ip_address(self):
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = 'Неизвестный IP'
        return ip


class CustomFormatter(logging.Formatter):
    def format(self, record):
        if not hasattr(record, 'ip_address'):
            record.ip_address = 'Неизвестный IP'
        return super().format(record)


def setup_logging():
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # Настройка обработчика и форматтера
    handler = logging.FileHandler(log_file_path)
    formatter = CustomFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(ip_address)s')
    handler.setFormatter(formatter)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.addFilter(IPFilter())

    logging.getLogger('apscheduler').setLevel(logging.CRITICAL)
    logging.getLogger('apscheduler.scheduler').setLevel(logging.CRITICAL)

    return logger


# Очистка логов
def clear_logs():
    for filename in os.listdir(log_directory):
        file_path = os.path.join(log_directory, filename)
        if os.path.isfile(file_path):
            with open(file_path, 'w'):
                pass
    logger = logging.getLogger(__name__)
    logger.info("Logs have been cleared.")


def setup_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.start()

    scheduler.add_job(
        clear_logs,
        trigger=IntervalTrigger(minutes=50),
        replace_existing=True
    )
    return scheduler
