import time
import secrets
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi.params import Body
from email_validator import validate_email, EmailNotValidError
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response, APIRouter, Query, Form
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.hash import argon2
from pydantic import BaseModel, EmailStr
from starlette.middleware.base import BaseHTTPMiddleware

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from routers.session import open_conn
from utils import send_message_email_verification


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
    is_deleted: bool = False


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="authorization/login")
app = FastAPI()


def get_password_hash(password: str) -> str:
    """
    Хэширует пароль пользователя с помощью алгоритма Argon2.

    :param password: Пароль для хэширования.
    :return: Хэшированный пароль.
    """
    return argon2.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет совпадение заданного пароля с хэшированным.

    :param plain_password: Заданный пароль (в обычном виде).
    :param hashed_password: Хэшированный пароль.
    :return: True при совпадении паролей, иначе False.
    """
    return argon2.verify(plain_password, hashed_password)


def check_password(password: str) -> None:
    """
    Проверяет пароль на соответствие требованиям:
    - Пароль содержит не менее 8 и не более 16 символов.
    - В пароле содержится хотя бы одна цифра.
    - В пароле содержится хотя бы одна буква.

    :param password: Проверяемый пароль.
    :raises HTTPException: При несоответствии пароля требованиям.
    """
    if len(password) < 8 or len(password) > 16:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароль должен содержать не менее 8 и не более 16 символов."
        )
    if not any(symbol.isalpha() for symbol in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароль должен содержать хотя бы одну букву."
        )
    if not any(symbol.isdigit() for symbol in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароль должен содержать хотя бы одну цифру."
        )


def check_username(name: str):
    if len(name) < 2 or len(name) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя должно содержать от 2 до 50 символов."
        )


def check_birthday(birthday: date):
    today = date.today()
    age = today.year - birthday.year - (
                (today.month, today.day) < (birthday.month, birthday.day))
    if age < 16:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Возраст пользователя должен быть не менее 16 лет."
        )

    if birthday > today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Дата рождения не может быть в будущем."
        )


def check_position(position: str):
    if len(position) < 2 or len(position) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Должность должна содержать от 2 до 100 символов."
        )


def check_height(height: int):
    if height < 50 or height > 300:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Рост должен быть в диапазоне от 50 до 300 см."
        )


def check_biography(biography: Optional[str]):
    if biography and len(biography) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Информация о себе не должна превышать 500 символов. "
        )


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Создает JWT токен доступа.

    :param data: Данные для кодирования в токене.
    :param expires_delta: Время жизни токена. По умолчанию использует переменную окружения.
    :return: JWT токен.
    """
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
    """
    Получает информацию о пользователе на основе JWT токена.

    :param jwt_token: JWT токен из заголовка авторизации.
    :return: Информация о пользователе.
    :raises HTTPException: Если токен недействителен или не удалось найти данные.
    """
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
                               "communication_id, biography, password, is_deleted FROM users WHERE email = %s",
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
                    profile_image=f"/photos/profile_photo/?user_id={user_data[0]}" if profile_image else None,
                    is_deleted=user_data[12]
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
    """
    Предоставляет информацию о пользователе на основе полученного токена.

    :param current_user: Текущий пользователь, полученный и токена.
    :return: Информация о текущем пользователе.
    """
    return current_user


@authorization_router.get('/user/me/dict', response_model=Dict[str, Any],
                          name='Получение пользователя в виде словаря по токену')
def read_user_me_dict(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Предоставляет информацию о пользователе в виде словаря на основе полученного токена.

    :param current_user: Текущий пользователь, полученный и токена.
    :return: Информация о текущем пользователе в виде словаря.
    """
    return current_user.dict()


@authorization_router.get('/interests/', response_model=List[Interest],
                          name="Получение списка интересов")
def get_interests() -> List[Interest]:
    """
    Предоставляет список интересов.

    :return: Список интересов.
    :raises HTTPException: При внутренней ошибке сервера.
    """
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


temp_storage = {}


@authorization_router.get("/confirm/{token}")
def confirm_email(token: str):
    user_data = temp_storage.get(token)
    if not user_data:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    user_values = (
        user_data["email"],
        user_data["password"],
        user_data["name"],
        user_data["city"],
        user_data["birthday"],
        user_data["position"],
        user_data["height"],
        user_data["gender_id"],
        user_data["target_id"],
        user_data["communication_id"],
        user_data["biography"]
    )
    interests_value = user_data["interests"]

    insert_query = """
                        INSERT INTO users (email, password, name, city, birthday, position, height, gender_id, target_id, communication_id, biography)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """
    filters_query = """
                            INSERT INTO filters (user_id, age_min, age_max, height_min, height_max, communication_id, target_id, gender_id, city, is_deleted)
                            VALUES (%s, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
                        """

    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(insert_query, user_values)
                user_id = cursor.fetchone()[0]
                cursor.execute(filters_query, (user_id,))
                if interests_value:
                    interests_query = """
                                        INSERT INTO users_interests (user_id, interest_id)
                                        VALUES (%s, (SELECT id FROM interests WHERE title = %s))
                                    """
                    cursor.executemany(
                        interests_query,
                        [(user_id, interest) for interest in interests_value]
                    )
                connection.commit()
                del temp_storage[token]
                access_token = create_access_token(data={"sub": user_data["email"]})
                return {"access_token": access_token, "token_type": "bearer"}
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
             interests: Optional[List[str]] = Query(None), biography: Optional[str] = None):
    """
    Регистрирует нового пользователя в системе.

    :param email: Электронная почта пользователя.
    :param password: Пароль пользователя.
    :param name: Имя пользователя.
    :param city: Город пользователя.
    :param birthday: День рождения пользователя.
    :param position: Должность пользователя.
    :param height: Рост пользователя.
    :param gender_id: Пол пользователя.
    :param target_id: Цель общения пользователя.
    :param communication_id: Предпочитаемый способ коммуникации пользователя.
    :param interests: Интересы пользователя.
    :param biography: Поле "о себе".
    :return: Словарь, содержащий токен доступа и тип токена.
    :raises HTTPException: В случае неверного email, некорректного пароля или внутренней ошибки сервера.
    """
    try:
        # Проверка корректности email
        try:
            validated_email = validate_email(email)
            email = validated_email.email
        except EmailNotValidError as ex:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неверный адрес электронной почты: {str(ex)}"
            )
        check_password(password)
        check_username(name)
        check_birthday(birthday)
        check_position(position)
        check_height(height)
        check_biography(biography)

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

                token = secrets.token_urlsafe(16)
                hashed_password = get_password_hash(password)
                temp_storage[token] = {
                    "email": email,
                    "password": hashed_password,
                    "name": name, "city": city,
                    "birthday": birthday,
                    "position": position,
                    "height": height,
                    "gender_id": gender_id,
                    "target_id": target_id,
                    "communication_id": communication_id,
                    "interests": interests,
                    "biography": biography

                }
                send_message_email_verification(email,token)
                return "message:" " Подтвердите регистрацию на почте "
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(ex)}"
        )





@authorization_router.post('/login', response_model=Dict[str, str], name='Вход в систему')
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Dict[str, str]:
    """
    Осуществляет вход пользователя в систему и возвращает токен доступа.

    :param form_data: Данные, содержащие имя пользователя и пароль.
    :return: Словарь, содержащий токен доступа и тип токена.
    :raises HTTPException: В случае неверных учетных данных, внутренней ошибке сервера.
    """
    email = form_data.username
    password = form_data.password

    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT password, is_deleted FROM users WHERE email = %s", (email,))
                user_data = cursor.fetchone()
                if user_data is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Неверные почта или пароль",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                if user_data[1]:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Профиль удалён",
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
                return {"access_token": access_token, "token_type": "bearer"}
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(ex)}"
        )


@authorization_router.post('/profile/interest/', status_code=status.HTTP_200_OK,
                           name="Добавление нового интереса для пользователя")
def add_interest(interest_title: str, current_user: User = Depends(get_current_user)):
    """
    Добавляет новое увлечение для текущего пользователя.

    :param interest_title: Название увлечения, которое нужно добавить.
    :param current_user: Текущий пользователь, полученный из токена.
    :return: Словарь с сообщением о результате операции.
    :raises HTTPException: Если увлечение не найдено, уже добавлено или возникла внутренняя ошибка сервера.
    """
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM interests WHERE title = %s",
                               (interest_title,))
                new_interest = cursor.fetchone()
                if not new_interest:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Интерес не найден"
                    )
                interest_id = new_interest[0]
                cursor.execute("SELECT * FROM users_interests WHERE user_id = %s AND interest_id = %s",
                               (current_user.id, interest_id))
                if cursor.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Этот интерес уже добавлен"
                    )
                cursor.execute("INSERT INTO users_interests(user_id, interest_id) VALUES (%s, %s)",
                               (current_user.id, interest_id))
                return {"detail": "Интерес добавлен"}
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера {str(ex)}"
        )


@authorization_router.patch('/update_profile', response_model=User, name='Обновление профиля')
def update_profile(
        current_user: User = Depends(get_current_user),
        email: Optional[EmailStr] = Body(None),
        name: Optional[str] = Body(None),
        city: Optional[str] = Body(None),
        birthday: Optional[date] = Body(None),
        position: Optional[str] = Body(None),
        height: Optional[int] = Body(None),
        gender_id: Optional[int] = Body(None),
        target_id: Optional[int] = Body(None),
        communication_id: Optional[int] = Body(None),
        biography: Optional[str] = Body(None)) -> User:
    """
    Обновляет поля анкеты текущего пользователя.

    :param current_user: Текущий пользователь, полученый по токену.
    :param email: Новая почта пользователя.
    :param name: Новое имя пользователя.
    :param city: Новый город пользователя.
    :param birthday: Новая дата рождения пользователя.
    :param position: Новая должность пользователя.
    :param height: Новый рост пользователя.
    :param gender_id: Новый идентификатор пола пользователя.
    :param target_id: Новый идентификатор цели общения пользователя.
    :param communication_id: Новый идентификатор предпочитаемого способа связи.
    :param biography: Новая информация в поле "о себе" пользователя.
    :return: Обновлённая анкета пользователя.
    :raises HTTPException: Если пользователь не найден или возникла внутренняя ошибка сервера.
    """
    try:
        if email:
            try:
                validated_email = validate_email(email)
                email = validated_email.email
            except EmailNotValidError as ex:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Неверный адрес электронной почты: {str(ex)}"
                )

            if name:
                check_username(name)
            if birthday:
                check_birthday(birthday)
            if position:
                check_position(position)
            if height:
                check_height(height)
            if biography:
                check_biography(biography)

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

                cursor.execute(
                    """
                    SELECT id, email, name, city, birthday, position, height, gender_id, target_id, communication_id, 
                    biography 
                    FROM users WHERE id = %s
                    """,
                    (current_user.id,))

                new_info = cursor.fetchone()

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
                    biography=new_info[10]
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
    """
    Изменяет пароль текущего пользователя.

    :param old_password: Старый пароль, который нужно изменить.
    :param new_password: Новый пароль.
    :param current_user: Текущий пользователь, полученный по токену.
    :return: Словарь с сообщением о результате операции.
    :raises HTTPException: Если пользователь не найден, старый пароль неверен или возникла внутренняя ошибка сервера.
    """
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
    """
    Удаляет профиль текущего пользователя.

    :param current_user: Текущий пользователь, полученный по токену.
    :return: HTTP-ответ с кодом состояния 204 (Нет содержимого).
    :raises HTTPException: Если пользователь не найден или возникла внутренняя ошибка сервера.
    """
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET is_deleted = %s
                    WHERE id = %s
                    RETURNING id, email, name, city, birthday, position, height, gender_id, target_id, communication_id, 
                    biography
                    """,
                    (True, current_user.id)
                )
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


@authorization_router.delete('/profile/interest/{interest_id}', status_code=status.HTTP_200_OK,
                             name="Удаление интереса")
def delete_interest(interest_id: int, current_user: User = Depends(get_current_user)):
    """
    Удаляет увлечение у текущего пользователя.

    :param interest_id: Идентификатор удаляемого увлечения.
    :param current_user: Текущий пользователь, полученный по токену.
    :return: Словарь с сообщением о результате операции.
    :raises HTTPException: Если увлечение не найдено или возникла внутренняя ошибка сервера.
    """
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM users_interests WHERE user_id = %s AND interest_id = %s",
                               (current_user.id, interest_id))
                if cursor.rowcount == 0:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Интерес не найден"
                    )
                return {"detail": "Успешное удаление"}
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутреннняя ошибка сервера: {str(ex)}"
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_attempts: int, period: int) -> None:
        """
        Middleware для ограничения количества попыток входа.

        :param app: Приложение.
        :param max_attempts: Максимальное количество попыток.
        :param period: Период ограничения попыток входа (в секундах).
        """
        super().__init__(app)
        self.max_attempts = max_attempts
        self.period = period
        self.attempts = {}

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Проверяет и ограничивает количество попыток входа по IP-адресу.

        :param request: HTTP-запрос.
        :param call_next: Функция для вызова следующего обработчика.
        :return: HTTP-ответ.
        """
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
