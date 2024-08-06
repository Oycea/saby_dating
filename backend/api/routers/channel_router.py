from datetime import datetime
from typing import Optional, List, Any
import psycopg2

from fastapi import HTTPException, APIRouter, Depends
from psycopg2.extras import RealDictCursor

from routers.session import open_conn
from routers.authorization_router import get_current_user, User

channel_router = APIRouter(prefix='/channels', tags=['Channels'])


@channel_router.get('/get_all_channels', name='Get all channels')
def get_channel() -> dict[str, int | Any]:
    try:
        with open_conn() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM channels")
                channels = cursor.fetchall()

                if not channels:
                    raise HTTPException(status_code=404, detail="Channels not found")

                return {'size': len(channels), 'channels info': channels}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@channel_router.get('/get_channel/{channel_id}', name='Get channel by channel_id')
def get_channel(channel_id: int) -> dict:
    try:
        with open_conn() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM channels WHERE id=%s", (channel_id,))
                channel = cursor.fetchone()

                if not channel:
                    raise HTTPException(status_code=404, detail="Channel not found")

                return channel
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@channel_router.get('/get_channel_users/{channel_id}', name='Get channel users by channel_id')
def get_channel_users(channel_id: int) -> dict[str, int | list]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM channels_users WHERE channel_id=%s", (channel_id,))
                channel_data = cursor.fetchall()

                if not channel_data:
                    raise HTTPException(status_code=404, detail="Users or channel not found")

                channel_users = [user[1] for user in channel_data]
                return {'size': len(channel_users), 'users': channel_users}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@channel_router.post('/create_new_channel/', name='Create new channel')
def create_new_channel(title: str, current_user: User = Depends(get_current_user)) -> dict:
    try:
        with open_conn() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                creator_id = current_user.id

                cursor.execute("INSERT INTO channels (title) VALUES (%s) RETURNING *", (title,))
                channel = cursor.fetchone()
                channel_id = channel[0]

                cursor.execute("INSERT INTO channels_users (channel_id, user_id) VALUES (%s, %s)",
                               (channel_id, creator_id))

                if not channel:
                    raise HTTPException(status_code=404, detail="Channel not found")

                return channel
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@channel_router.post('/add_user_to_the_channel/{channel_id}/{user_id}',
                     name='Add user to the channel by user_id and channel_id')
def add_user_to_the_channel(channel_id: int, current_user: User = Depends(get_current_user)) -> dict[str, int | list]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                user_id = current_user.id

                cursor.execute("INSERT INTO channels_users (channel_id, user_id) VALUES (%s, %s)",
                               (channel_id, user_id))

                cursor.execute("SELECT user_id FROM channels_users WHERE channel_id=%s", (channel_id,))
                channel_users = cursor.fetchall()

                if not channel_users:
                    raise HTTPException(status_code=404, detail="Users or channel not found")

                users = [user[0] for user in channel_users]
                connection.rollback()
                return {'size': len(users), 'users': users}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
