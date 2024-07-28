from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from pydantic import BaseModel, EmailStr, Field
from passlib.hash import argon2
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import psycopg2
from psycopg2 import sql
from email_validator import validate_email, EmailNotValidError
from typing import Generator, Optional, Dict
import time
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
from datetime import datetime, timedelta

DATABASE_URL = "postgresql://postgres:umbrella@localhost:5432/mydb"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str
    date_of_birth: str
    gender: str
    city: str
    position: str
    communication_goal: str


class Token(BaseModel):
    access_token: str
    token_type: str


def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


SECRET_KEY = ""
ALGORITHM = ""
ACCESS_TOKEN_EXPIRE_MINUTES = 30
app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_password_hash(password: str) -> str:
    return argon2.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return argon2.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return email


@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Generator = Depends(get_db)) -> Dict[str, str]:
    email = user.email
    password = user.password

    try:
        # Проверка корректности email
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid email address: {str(e)}"
        )

    try:
        with db.cursor() as cur:
            # Проверка email
            cur.execute(sql.SQL("SELECT id FROM users WHERE email = %s"),
                        [email])
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )

            hashed_password = get_password_hash(password)
            cur.execute(sql.SQL(
                """
                INSERT INTO users (email, hashed_password, name, date_of_birth, gender, city, position, communication_goal)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, email, name, date_of_birth, gender, city, position, communication_goal
                """),
                [user.email, hashed_password, user.name, user.date_of_birth,
                 user.gender, user.city, user.position,
                 user.communication_goal])
            db.commit()
            return {"email": email}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/login", response_model=dict)
def login(form_data: OAuth2PasswordRequestForm = Depends(),
          db: Generator = Depends(get_db)) -> Dict[str, str]:
    email = form_data.username
    password = form_data.password

    try:
        with db.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT hashed_password FROM users WHERE email = %s"),
                [email])
            result = cur.fetchone()
            if result is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            hashed_password = result[0]
            if not verify_password(password, hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            access_token = create_access_token(data={"sub": email})
            return {"access_token": access_token, "token_type": "bearer"}
    finally:
        db.close()


@app.get("/")
def read_root() -> Dict[str, str]:
    return {"message": "Welcome to the user registration and login system"}


@app.get("/users/me", response_model=dict[str, str])
def read_users_me(current_user: str = Depends(get_current_user)):
    return {"email": current_user}


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

        self.attempts[client_ip] = [t for t in self.attempts[client_ip] if
                                    t > current_time - self.period]

        if len(self.attempts[client_ip]) >= self.max_attempts:
            return Response("Too many login attempts, please try again later",
                            status_code=429)

        response = await call_next(request)
        if request.url.path == "/login" and response.status_code == 200:
            self.attempts[client_ip].append(current_time)
        return response


app.add_middleware(RateLimitMiddleware, max_attempts=5, period=60)
