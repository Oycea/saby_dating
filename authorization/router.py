from fastapi import APIRouter
from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm
from email_validator import validate_email, EmailNotValidError
from typing import Generator
from session import get_database_connection

router = APIRouter(
    prefix="/authorization",
    tags=["Authorization"]
)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str
    date_of_birth: str
    gender: str
    city: str
    position: str
    communication_goal: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Generator = Depends(get_database_connection)):
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
            cur.execute('SELECT "id" FROM "user" WHERE "email" = %s', [email])
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )

            hashed_password = get_password_hash(password)
            cur.execute(
                '''
                INSERT INTO "user" (email, hashed_password, name, date_of_birth, gender, city, position, communication_goal)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, email, name, date_of_birth, gender, city, position, communication_goal
                ''',
                [user.email, hashed_password, user.name, user.date_of_birth,
                 user.gender, user.city, user.position, user.communication_goal])
            return {"email": email}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/login", response_model=dict)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Generator = Depends(get_database_connection)):
    email = form_data.username
    password = form_data.password

    try:
        with db.cursor() as cur:
            cur.execute('SELECT "hashed_password" FROM "user" WHERE "email" = %s', [email])
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

            return {"access_token": email, "token_type": "bearer"}
    finally:
        db.close()

