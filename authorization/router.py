from fastapi import Depends, HTTPException, status, Request, Response, APIRouter
from pydantic import BaseModel, EmailStr, Field
from passlib.hash import argon2
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from email_validator import validate_email, EmailNotValidError
from typing import Dict, Any
import time
from starlette.middleware.base import BaseHTTPMiddleware
from session import get_database_connection
from datetime import date, datetime, timedelta
from jose import JWTError, jwt

router = APIRouter(prefix='', tags=['Authorization'])


SECRET_KEY = "secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str
    city: str
    birthday: date
    position: str
    height: int
    gender_id: int
    target_id: int
    communication_id: int


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


def get_password_hash(password: str) -> str:
    return argon2.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return argon2.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post('/register', status_code=status.HTTP_200_OK)
def register(user: UserCreate) -> Dict[str, str]:
    email = user.email
    password = user.password

    try:
        # Проверка корректности email
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid email address: {str(ex)}"
        )

    try:
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                # Проверка email
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                event = cursor.fetchone()
                if event:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered"
                    )

                hashed_password = get_password_hash(password)
                cursor.execute(
                    """
                    INSERT INTO users (email, password, name, city, birthday, position, height, gender_id, target_id, communication_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, email, password, name, city, birthday, position, height, gender_id, target_id, communication_id
                    """,
                    (email, hashed_password, user.name, user.city, user.birthday,
                     user.position, user.height, user.gender_id,
                     user.target_id, user.communication_id)
                )
            return {"email": email}
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(ex)}"
        )


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


@router.get('/get_current_user')
def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, email, name, city, birthday, position, height, gender_id, target_id, communication_id, password FROM users WHERE email = %s",
                               (email,)
                               )
                user_info = cursor.fetchone()
                if user_info is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Could not validate credentials",
                        headers={"WWW-Authenticate": "Basic"},
                    )
                user = User(
                    id=user_info[0],
                    email=user_info[1],
                    name=user_info[2],
                    city=user_info[3],
                    birthday=user_info[4],
                    position=user_info[5],
                    height=user_info[6],
                    gender_id=user_info[7],
                    target_id=user_info[8],
                    communication_id=user_info[9]
                )
                return user
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.post('/login', response_model=dict)
def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username
    password = form_data.password

    try:
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT password FROM users WHERE email = %s", (email,))
                event = cursor.fetchone()
                if event is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Incorrect email or password",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                hashed_password = event[0]
                if not verify_password(password, hashed_password):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Incorrect email or password",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                access_token = create_access_token(data={"sub": email})
                response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True)
                return {"access_token": access_token, "token_type": "bearer"}
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(ex)}"
        )


@router.get("/user/me", response_model=User)
def read_user_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/user/me/dict")
def read_user_me_dict(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    return current_user.dict()


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
            return Response("Try later", status_code=429)

        response = await call_next(request)
        if request.url.path == "/login/" and response.status_code == 200:
            self.attempts[client_ip].append(current_time)
        return response

