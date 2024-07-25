from fastapi import APIRouter, HTTPException
from typing import Optional

from routers.session import open_conn, close_conn

user_router = APIRouter(prefix='/users', tags=['Users'])


@user_router.get('/get_user/{user_id}', name='Get user')
def get_user(user_id: int):
    try:
        cursor, conn = open_conn()

        query = f'SELECT * FROM users WHERE id={user_id}'

        cursor.execute(query)
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=404, detail='User not found')
        return user
    finally:
        close_conn(cursor, conn)


@user_router.post('/create_user', name='Create user')
def create_user(username: str):
    try:
        cursor, conn = open_conn()

        query = f"INSERT INTO users (name) VALUES ('{username}');"

        cursor.execute(query)

        conn.commit()

        return {'message': f'User created successfully'}
    finally:
        close_conn(cursor, conn)


@user_router.delete('/delete_user/{user_id}', name='Delete user')
def delete_user(user_id: int):
    try:
        cursor, conn = open_conn()

        query = f'SELECT * FROM users WHERE id={user_id}'

        cursor.execute(query)
        user = cursor.fetchone()

        if not user:
            close_conn(cursor, conn)
            raise HTTPException(status_code=404, detail='User not found')

        query = f'DELETE FROM users WHERE id={user_id}'

        cursor.execute(query)

        conn.commit()

        return {'message': f'User {user_id} deleted successfully'}
    finally:
        close_conn(cursor, conn)

