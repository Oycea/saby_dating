from jose import JWTError, jwt
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from fastapi import HTTPException

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
    print(email)
    token = create_reset_password_token(email)
    reset_password_url = f"http://195.133.201.168:8000/password_reset.html/{token}"
    body = f"Ссылка для сброса пароля: {reset_password_url}"
    msg = MIMEText(body)
    msg['Subject'] = 'password reset'
    msg['From'] = 'datesaby@gmail.com'
    msg['To'] = email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.connect(SMTP_SERVER, SMTP_PORT)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise HTTPException(status_code=400, detail=f"Authentication error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    return token
