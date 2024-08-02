from fastapi import FastAPI, Depends, HTTPException, status, Request, Response, APIRouter, Query
from pydantic import BaseModel, EmailStr
from passlib.hash import argon2
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from email_validator import validate_email, EmailNotValidError
from typing import Dict, Any, Optional
import time
from starlette.middleware.base import BaseHTTPMiddleware
from routers.session import open_conn
from datetime import date, datetime, timedelta
from jose import JWTError, jwt
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

authorization_router = APIRouter(prefix='/authorization', tags=['Authorization'])


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
    biography: Optional[str] = None


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
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, email, name, city, birthday, position, height, gender_id, target_id, "
                               "communication_id, biography, password FROM users WHERE email = %s",
                               (email,)
                               )
                event = cursor.fetchone()
                if event is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Could not validate credentials",
                        headers={"WWW-Authenticate": "Basic"},
                    )
                user = User(
                    id=event[0],
                    email=event[1],
                    name=event[2],
                    city=event[3],
                    birthday=event[4],
                    position=event[5],
                    height=event[6],
                    gender_id=event[7],
                    target_id=event[8],
                    communication_id=event[9],
                    biography=event[10]
                )
                return user
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


@authorization_router.get('/user/me', response_model=User, name='Get user by token')
def read_user_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@authorization_router.get('/user/me/dict', response_model=User,
                          name='Get user as dictionary by token')
def read_user_me_dict(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    return current_user.dict()


@authorization_router.post('/register/', status_code=status.HTTP_200_OK,
                           name='Registers a new user')
def register(email: EmailStr, password: str, name: str, city: str,
             birthday: date, position: str, height: int, gender_id: int,
             target_id: int, communication_id: int, biography: Optional[str] = None) -> Dict[str, str]:
    try:
        # Проверка корректности email
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid email address: {str(ex)}"
        )
    check_password(password)
    try:
        with open_conn() as connection:
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
                    INSERT INTO users (email, password, name, city, birthday, position, height, gender_id, target_id, 
                    communication_id, biography)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (email, hashed_password, name, city, birthday, position,
                     height, gender_id, target_id, communication_id, biography)
                )
                access_token = create_access_token(data={"sub": email})
                return {"access_token": access_token, "token_type": "bearer"}
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(ex)}"
        )


@authorization_router.post('/login/', response_model=dict, name='Login')
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username
    password = form_data.password

    try:
        with open_conn() as connection:
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
                return {"access_token": access_token, "token_type": "bearer"}
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(ex)}"
        )


@authorization_router.patch('/profile/', response_model=User, name='Update profile')
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
        biography: Optional[str] = Query(None)) -> User:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT email, name, city, birthday, position, height, gender_id, target_id, communication_id, biography 
                    FROM users WHERE id = %s
                    """,
                    (current_user.id,))

                current_data = cursor.fetchone()
                if not current_data:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User not found"
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
                    SET email = %s, name = %s, city = %s, birthday = %s, position = %s, height = %s, gender_id = %s, target_id = %s, communication_id = %s, biography = %s
                    WHERE id = %s
                    RETURNING id, email, name, city, birthday, position, height, gender_id, target_id, communication_id, biography
                    """,
                    (updated_data["email"], updated_data["name"],
                     updated_data["city"], updated_data["birthday"],
                     updated_data["position"], updated_data["height"],
                     updated_data["gender_id"], updated_data["target_id"],
                     updated_data["communication_id"], updated_data["biography"],
                     current_user.id)
                )

                new_info = cursor.fetchone()
                if not new_info:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to update user"
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
            detail=f"Internal server error: {str(ex)}"
        )


@authorization_router.delete('/profile/', status_code=status.HTTP_204_NO_CONTENT,
                             name='Delete profile')
def delete_profile(current_user: User = Depends(get_current_user)):
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM users WHERE id = %s", (current_user.id,))
                if cursor.rowcount == 0:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User not found"
                    )
                return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(ex)}"
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
            return Response("Try later", status_code=429)

        response = await call_next(request)
        if request.url.path == "/login/" and response.status_code == 200:
            self.attempts[client_ip].append(current_time)
        return response


app.add_middleware(RateLimitMiddleware, max_attempts=5, period=60)
