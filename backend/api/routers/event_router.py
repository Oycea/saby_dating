import datetime
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, APIRouter
from routers.session import open_conn

event_router = APIRouter(prefix='/events', tags=['Events'])


@event_router.get('/get_event/{event_id}', name='Get event by id')
def get_event(event_id: int) -> tuple:
    with open_conn() as connection:
        with connection.cursor() as cursor:
            try:
                cursor.execute("SELECT * FROM events WHERE id=%s", (event_id,))
                event = cursor.fetchone()

                if not event:
                    raise HTTPException(status_code=404, detail='Event not found')
                return event
            finally:
                print('Ok')


@event_router.post('/create_event', name='Create new event')
def create_event(title: str, description: str, place: str, tags: list[str],
                 users: list[int], creator_id: int, date: datetime, is_distant: bool = False,
                 images_url: Optional[list[str]] = None, users_limit: Optional[int] = None) -> dict[str, str]:
    with open_conn() as connection:
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    "INSERT INTO events (title, description, place, created_at, datetime, creator_id, users_limit, "
                    "online) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *;",
                    (title, description, place, datetime.now, date, creator_id, users_limit, is_distant))
                event = cursor.fetchone()

                for i in range(len(tags)):
                    cursor.execute("SELECT id FROM tags WHERE title=%s", (tags[i],))
                    tag = cursor.fetchone()

                    cursor.execute("INSERT INTO events_tags VALUES (%s, %s);", (event[0], tag[0]))

                for i in range(len(users)):
                    cursor.execute("INSERT INTO events_users VALUES (%s, %s);", (event[0], users[i]))

                for i in range(len(images_url)):
                    cursor.execute("INSERT INTO events_images VALUES (%s, %s);", (event[0], images_url[i]))

                return {'message': f'Event {event[0]} created successfully',
                        'event info': f'{event}'}
            finally:
                print('Ok')


@event_router.delete('/delete_event/{event_id}', name='Delete event by id')
def delete_event(event_id: int) -> dict[str, str]:
    with open_conn() as connection:
        with connection.cursor() as cursor:
            try:
                cursor.execute('DELETE FROM events WHERE id=%s RETURNING *', (event_id,))
                event = cursor.fetchone()

                if not event:
                    raise HTTPException(status_code=404, detail='Event not found')

                return {'message': f'Event {event_id} deleted successfully',
                        'deleted event info': f'{event}'}
            finally:
                print('Ok')
