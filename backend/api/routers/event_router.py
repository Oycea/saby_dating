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

                return event
            except Exception as ex:
                raise ex
            finally:
                print('Connection closed')


@event_router.post('/create_event/', name='Create new event')
def create_event(title: str, description: str, place: str, tags: list[str],
                 users: list[int], date: datetime, creator_id: int, images_url: Optional[list[str]] = None,
                 users_limit: Optional[int] = None, is_distant: bool = False) -> dict[str, str]:
    with open_conn() as connection:
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    "WITH new_event AS("
                    "INSERT INTO events (title, description, place, created_at, datetime, creator_id, users_limit, "
                    "online) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                    "RETURNING *)"
                    "SELECT * FROM new_event",
                    (title, description, place, datetime.now(), date, creator_id, users_limit, is_distant))
                event = cursor.fetchone()

                for i in range(len(tags)):
                    cursor.execute("SELECT id FROM tags WHERE title=%s", (tags[i],))
                    tag = cursor.fetchone()
                    cursor.execute("INSERT INTO events_tags VALUES (%s, %s);", (event[0], tag[0]))

                for i in range(len(users)):
                    cursor.execute("INSERT INTO events_users VALUES (%s, %s);", (event[0], users[i]))

                cursor.execute("INSERT INTO events_users VALUES (%s, %s);", (event[0], event[6]))

                for i in range(len(images_url)):
                    cursor.execute("INSERT INTO events_images VALUES (%s, %s);", (event[0], images_url[i]))

                return {'message': f'Event with id {event[0]} created successfully',
                        'event info': f'{event}'}
            except Exception as ex:
                raise ex
            finally:
                print('Connection closed')


@event_router.put('/edit_event_info/{event_id}/', name='Edit event by id')
def edit_event_info(event_id: int, title: Optional[str] = None,
                    description: Optional[str] = None,
                    place: Optional[str] = None,
                    date: Optional[datetime] = None, creator_id: Optional[int] = None,
                    users_limit: Optional[int] = None, is_distant: Optional[bool] = None) -> tuple:
    with open_conn() as connection:
        with connection.cursor() as cursor:
            try:
                cursor.execute("SELECT * FROM events WHERE id=%s", (event_id,))
                event = cursor.fetchone()

                if not title:
                    title = event[1]
                if not description:
                    description = event[2]
                if not place:
                    place = event[3]
                if not date:
                    date = event[5]
                if not creator_id:
                    creator_id = event[6]
                if not users_limit:
                    users_limit = event[7]
                if not is_distant:
                    is_distant = event[8]

                cursor.execute(
                    "UPDATE events SET (title, description, place, datetime, creator_id, users_limit,"
                    "online)="
                    "(%s, %s, %s, %s, %s, %s, %s)"
                    "WHERE id=%s "
                    "RETURNING *",
                    (title, description, place, date, creator_id, users_limit, is_distant, event_id))
                event = cursor.fetchone()

                return event
            except Exception as ex:
                raise ex
            finally:
                print('Connection closed ')


@event_router.delete('/delete_event/{event_id}', name='Delete event by id')
def delete_event(event_id: int) -> dict[str, str]:
    with open_conn() as connection:
        with connection.cursor() as cursor:
            try:
                cursor.execute('DELETE FROM events WHERE id=%s RETURNING *', (event_id,))
                event = cursor.fetchone()

                return {'message': f'Event {event_id} deleted successfully',
                        'deleted event info': f'{event}'}
            except Exception as ex:
                raise ex
            finally:
                print('Connection closed')
