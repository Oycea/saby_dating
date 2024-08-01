from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.hash import argon2
from fastapi import HTTPException, status

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from routers.session import open_conn


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
            # Проверка email
            cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            if not user:
                return False
            return True


def get_password_hash(password: str) -> str:
    return argon2.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return argon2.verify(plain_password, hashed_password)


def check_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    if not any(symb.isalpha() for symb in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one letter"
        )
    if not any(symb.isdigit() for symb in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least one digit"
        )
    if not any(symb in '!=+$@#%^' for symb in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The password must contain at least one special character (!=+$@#%^)"
        )


def change_password(email: str, password: str):
    with open_conn() as connection:
        with connection.cursor() as cursor:
            check_password(password)
            hashed_password = get_password_hash(password)
            cursor.execute("""UPDATE users SET password = %s WHERE email = %s""", (hashed_password, email))
            connection.commit()
            print("password updated successfully")
