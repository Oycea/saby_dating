import time
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional, List

from email_validator import validate_email, EmailNotValidError
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response, APIRouter, Query, Form
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.hash import argon2
from pydantic import BaseModel, EmailStr
from starlette.middleware.base import BaseHTTPMiddleware

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from routers.session import open_conn

authorization_router = APIRouter(prefix='/authorization', tags=['Authorization'])


class Interest(BaseModel):
    id: int
    subject: str
    title: str


class User(BaseModel):
    id: int
    email: str
    name: str
    city: str
    birthday: date
    position: str
    height: int
    gender_id: int
    target_id: int
    communication_id: int
    interests: List[Interest] = []
    biography: Optional[str] = None
    profile_image: Optional[str] = None


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="authorization/login/")
app = FastAPI()


def get_password_hash(password: str) -> str:
    return argon2.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return argon2.verify(plain_password, hashed_password)


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


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@authorization_router.get('/get_current_user')
def get_current_user(jwt_token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Не удалось подтвердить данные",
                headers={"WWW-Authenticate": "Bearer"},
            )
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, email, name, city, birthday, position, height, gender_id, target_id, "
                               "communication_id, biography, password FROM users WHERE email = %s",
                               (email,)
                               )
                user_data = cursor.fetchone()
                if user_data is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Не удалось подтвердить данные",
                        headers={"WWW-Authenticate": "Basic"},
                    )
                cursor.execute(
                    "SELECT i.id, i.subject, i.title FROM users_interests ui JOIN interests i ON ui.interest_id = i.id WHERE ui.user_id = %s",
                    (user_data[0],))
                interests = [Interest(id=interest[0], subject=interest[1],
                                      title=interest[2]) for interest in
                             cursor.fetchall()]

                cursor.execute(
                    "SELECT id FROM users_images WHERE user_id = %s AND is_profile_image = TRUE",
                    (user_data[0],)
                    )
                profile_image = cursor.fetchone()

                user = User(
                    id=user_data[0],
                    email=user_data[1],
                    name=user_data[2],
                    city=user_data[3],
                    birthday=user_data[4],
                    position=user_data[5],
                    height=user_data[6],
                    gender_id=user_data[7],
                    target_id=user_data[8],
                    communication_id=user_data[9],
                    interests=interests,
                    biography=user_data[10],
                    profile_image=f"/photos/profile_photo/?user_id={user_data[0]}" if profile_image else None
                )
                return user
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось подтвердить данные",
            headers={"WWW-Authenticate": "Bearer"}
        )


@authorization_router.get('/user/me', response_model=User, name='Получение пользователя по токену')
def read_user_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@authorization_router.get('/user/me/dict', response_model=Dict[str, Any],
                          name='Получение пользователя в виде словаря по токену')
def read_user_me_dict(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    return current_user.dict()


@authorization_router.get('/interests/', response_model=List[Interest],
                          name="Получение списка интересов")
def get_interests() -> List[Interest]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, subject, title FROM interests")
                interests = cursor.fetchall()
                return [Interest(id=interest[0], subject=interest[1], title=interest[2]) for interest in interests]
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(ex)}"
        )


@authorization_router.post('/register/', status_code=status.HTTP_200_OK,
                           name='Регистрация нового пользователя')
def register(email: EmailStr, password: str, name: str, city: str,
             birthday: date, position: str, height: int, gender_id: int,
             target_id: int, communication_id: int,
             interests: Optional[List[str]] = [], biography: Optional[str] = None) -> Dict[str, str]:
    try:
        # Проверка корректности email
        validated_email = validate_email(email)
        email = validated_email.email
    except EmailNotValidError as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неверный адрес электронной почты: {str(ex)}"
        )
    check_password(password)
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                # Проверка email
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                user_data = cursor.fetchone()
                if user_data:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Почта уже зарегистрирована"
                    )

                hashed_password = get_password_hash(password)
                cursor.execute(
                    """
                    INSERT INTO users (email, password, name, city, birthday, position, height, gender_id, target_id, 
                    communication_id, biography)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (email, hashed_password, name, city, birthday, position,
                     height, gender_id, target_id, communication_id, biography)
                )
                user_id = cursor.fetchone()[0]

                if interests:
                    cursor.executemany(
                        "INSERT INTO users_interests (user_id, interest_id) VALUES (%s, (SELECT id FROM interests WHERE title = %s))",
                        [(user_id, interest) for interest in interests]
                    )

                access_token = create_access_token(data={"sub": email})
                return {"access_token": access_token, "token_type": "bearer"}
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(ex)}"
        )


@authorization_router.post('/login', response_model=Dict[str, str], name='Вход в систему')
def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()) -> Dict[str, str]:
    email = form_data.username
    password = form_data.password

    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT password FROM users WHERE email = %s", (email,))
                user_data = cursor.fetchone()
                if user_data is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Неверные почта или пароль",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                hashed_password = user_data[0]
                if not verify_password(password, hashed_password):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Неверные почта или пароль",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                access_token = create_access_token(data={"sub": email})
                response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True)
                return {"access_token": access_token, "token_type": "bearer"}
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(ex)}"
        )


@authorization_router.patch('/profile/', response_model=User, name='Обновление профиля')
def update_profile(
        current_user: User = Depends(get_current_user),
        email: Optional[EmailStr] = Query(None),
        name: Optional[str] = Query(None),
        city: Optional[str] = Query(None),
        birthday: Optional[date] = Query(None),
        position: Optional[str] = Query(None),
        height: Optional[int] = Query(None),
        gender_id: Optional[int] = Query(None),
        target_id: Optional[int] = Query(None),
        communication_id: Optional[int] = Query(None),
        interests: Optional[List[str]] = Query(None),
        biography: Optional[str] = Query(None)) -> User:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT email, name, city, birthday, position, height, gender_id, target_id, communication_id, 
                    biography 
                    FROM users WHERE id = %s
                    """,
                    (current_user.id,))

                current_data = cursor.fetchone()
                if not current_data:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Пользователь не найден"
                    )

                updated_data = {
                    "email": email or current_data[0],
                    "name": name or current_data[1],
                    "city": city or current_data[2],
                    "birthday": birthday or current_data[3],
                    "position": position or current_data[4],
                    "height": height or current_data[5],
                    "gender_id": gender_id or current_data[6],
                    "target_id": target_id or current_data[7],
                    "communication_id": communication_id or current_data[8],
                    "biography": biography or current_data[9]
                }

                cursor.execute(
                    """
                    UPDATE users
                    SET email = %s, name = %s, city = %s, birthday = %s, position = %s, height = %s, gender_id = %s, 
                    target_id = %s, communication_id = %s, biography = %s
                    WHERE id = %s
                    RETURNING id, email, name, city, birthday, position, height, gender_id, target_id, communication_id, 
                    biography
                    """,
                    (updated_data["email"], updated_data["name"],
                     updated_data["city"], updated_data["birthday"],
                     updated_data["position"], updated_data["height"],
                     updated_data["gender_id"], updated_data["target_id"],
                     updated_data["communication_id"], updated_data["biography"],
                     current_user.id)
                )

                if interests is not None:
                    cursor.execute(
                        "DELETE FROM users_interests WHERE user_id = %s",
                        (current_user.id,))
                    cursor.executemany(
                        "INSERT INTO users_interests (user_id, interest_id) VALUES (%s, (SELECT id FROM interests WHERE title = %s))",
                        [(current_user.id, interest) for interest in interests]
                    )

                cursor.execute(
                    """
                    SELECT id, email, name, city, birthday, position, height, gender_id, target_id, communication_id, 
                    biography 
                    FROM users WHERE id = %s
                    """,
                    (current_user.id,))

                new_info = cursor.fetchone()

                cursor.execute(
                    "SELECT i.id, i.subject, i.title FROM users_interests ui JOIN interests i ON ui.interest_id = i.id WHERE ui.user_id = %s",
                    (current_user.id,))
                new_interests = [Interest(id=interest[0], subject=interest[1],
                                          title=interest[2]) for interest in cursor.fetchall()]

                if not new_info:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Не удалось обновить информацию"
                    )

                return User(
                    id=new_info[0],
                    email=new_info[1],
                    name=new_info[2],
                    city=new_info[3],
                    birthday=new_info[4],
                    position=new_info[5],
                    height=new_info[6],
                    gender_id=new_info[7],
                    target_id=new_info[8],
                    communication_id=new_info[9],
                    biography=new_info[10],
                    interests=new_interests
                )
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(ex)}"
        )


@authorization_router.patch('/profile/change_password/', status_code=status.HTTP_200_OK,
                            name='Изменение пароля')
def change_password(
        old_password: str = Form(...),
        new_password: str = Form(...),
        current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT password FROM users WHERE id = %s",
                               (current_user.id,))
                user_password = cursor.fetchone()
                if user_password is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Пользователь не найден"
                    )
                hashed_old_password = user_password[0]
                if not verify_password(old_password, hashed_old_password):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Неверный старый пароль"
                    )
                check_password(new_password)
                hashed_new_password = get_password_hash(new_password)

                cursor.execute("UPDATE users SET password = %s WHERE id = %s",
                               (hashed_new_password, current_user.id))
                if cursor.rowcount == 0:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Не удалось обновить пароль"
                    )
                return {"detail": "Пароль изменён"}
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(ex)}"
        )


@authorization_router.delete('/profile/', status_code=status.HTTP_204_NO_CONTENT,
                             name='Удаление профиля')
def delete_profile(current_user: User = Depends(get_current_user)) -> Response:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM users WHERE id = %s", (current_user.id,))
                if cursor.rowcount == 0:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Пользователь не найден"
                    )
                return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(ex)}"
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_attempts: int, period: int) -> None:
        super().__init__(app)
        self.max_attempts = max_attempts
        self.period = period
        self.attempts = {}

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host
        current_time = time.time()

        if client_ip not in self.attempts:
            self.attempts[client_ip] = []

        self.attempts[client_ip] = [t for t in self.attempts[client_ip] if t > current_time - self.period]

        if len(self.attempts[client_ip]) >= self.max_attempts:
            return Response("Попробуйте позже", status_code=429)

        response = await call_next(request)
        if request.url.path == "/login/" and response.status_code == 200:
            self.attempts[client_ip].append(current_time)
        return response


app.add_middleware(RateLimitMiddleware, max_attempts=5, period=60)
