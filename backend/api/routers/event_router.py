import datetime

from fastapi import FastAPI, HTTPException, Depends, APIRouter
from typing import Optional
from datetime import datetime

from routers.session import open_conn, close_conn

event_router = APIRouter(prefix='/events', tags=['Events'])


@event_router.get('/get_event/{event_id}', name='Get event by id')
def get_event(event_id: int):
    try:
        cursor, conn = open_conn()

        query = f'SELECT * FROM events WHERE id={event_id}'

        cursor.execute(query)
        event = cursor.fetchone()

        if not event:
            raise HTTPException(status_code=404, detail='Event not found')
        return event
    finally:
        close_conn(cursor, conn)


@event_router.post('/create_event', name='Create new event')
def create_event(title: str, description: str, place: str, tags: list[str],
                 users: list[int], creator_id: int, date: datetime, is_distant: bool = False,
                 images_url: Optional[list[str]] = None, users_limit: Optional[int] = None):
    try:
        cursor, conn = open_conn()
        query = f"INSERT INTO events (title, description, place, created_at, datetime, creator_id, users_limit, online) " \
                f"VALUES ('{title}', '{description}', '{place}', '{datetime.now()}', " \
                f"'{date}', '{creator_id}', '{users_limit}', '{is_distant}') RETURNING *;"
        cursor.execute(query)
        event = cursor.fetchone()

        conn.commit()

        for i in range(len(tags)):
            query = f"SELECT id FROM tags WHERE title='{tags[i]}'"
            cursor.execute(query)
            tag = cursor.fetchone()

            query = f"INSERT INTO events_tags VALUES ({event[0]}, {tag[0]});"
            cursor.execute(query)

        conn.commit()

        for i in range(len(users)):
            query = f"INSERT INTO events_users VALUES ({event[0]}, {users[i]});"
            cursor.execute(query)

        conn.commit()

        return {'message': f'Event {event[0]} created successfully',
                'event info': f'{event}'}
    finally:
        close_conn(cursor, conn)


@event_router.delete('/delete_event/{event_id}', name='Delete event by id')
def delete_event(event_id: int):
    try:
        cursor, conn = open_conn()

        query = f'DELETE FROM events WHERE id={event_id} RETURNING *'

        cursor.execute(query)
        event = cursor.fetchone()

        if not event:
            raise HTTPException(status_code=404, detail='Event not found')

        conn.commit()

        return {'message': f'Event {event_id} deleted successfully',
                'deleted event info': f'{event}'}
    finally:
        close_conn(cursor, conn)

