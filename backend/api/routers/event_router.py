from datetime import datetime
from typing import Optional, List

from fastapi import HTTPException, APIRouter
from routers.session import open_conn

event_router = APIRouter(prefix='/events', tags=['Events'])


@event_router.get('/get_event/{event_id}', name='Get event by id')
def get_event(event_id: int) -> list:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM events WHERE id=%s", (event_id,))
                event = cursor.fetchone()
                if event is None:
                    raise HTTPException(status_code=404, detail="Event not found")
                return event
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.post('/create_event/', name='Create new event')
def create_event(title: str, description: str, place: str, tags: List[str],
                 date: datetime, creator_id: int, images_url: Optional[List[str]] = None,
                 users_limit: Optional[int] = None, is_distant: bool = False) -> dict[str, str]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "WITH new_event AS("
                    "INSERT INTO events (title, description, place, created_at, datetime, creator_id, users_limit, "
                    "online) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                    "RETURNING *)"
                    "SELECT * FROM new_event",
                    (title, description, place, datetime.now(), date, creator_id, users_limit, is_distant))
                event = cursor.fetchone()

                tags_query = "INSERT INTO events_tags (event_id, tag_id) VALUES "
                tags_data = []
                for tag in tags:
                    cursor.execute("SELECT id FROM tags WHERE title=%s", (tag,))
                    tag_id = cursor.fetchone()
                    tags_data.append((event[0], tag_id[0]))
                cursor.executemany(tags_query + "(%s, %s);", tags_data)

                cursor.execute("INSERT INTO events_users (event_id, user_id) VALUES (%s, %s)", (event[0], creator_id))

                if images_url:
                    images_query = "INSERT INTO events_images (event_id, url) VALUES "
                    images_data = [(event[0], url) for url in images_url]
                    cursor.executemany(images_query + "(%s, %s);", images_data)

                return {'message': f'Event with id {event[0]} created successfully', 'event info': f'{event}'}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.put('/edit_event_info/{event_id}/', name='Edit event by id')
def edit_event_info(event_id: int, title: Optional[str] = None,
                    description: Optional[str] = None,
                    place: Optional[str] = None,
                    date: Optional[datetime] = None, creator_id: Optional[int] = None,
                    users_limit: Optional[int] = None, is_distant: Optional[bool] = None) -> list:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM events WHERE id=%s", (event_id,))
                event = cursor.fetchone()

                if not event:
                    raise HTTPException(status_code=404, detail="Event not found")

                update_fields = {
                    'title': title or event[1],
                    'description': description or event[2],
                    'place': place or event[3],
                    'datetime': date or event[5],
                    'creator_id': creator_id or event[6],
                    'users_limit': users_limit or event[7],
                    'online': is_distant if is_distant is not None else event[8]
                }

                cursor.execute(
                    "UPDATE events SET title=%s, description=%s, place=%s, datetime=%s, creator_id=%s, "
                    "users_limit=%s, online=%s WHERE id=%s RETURNING *",
                    (*update_fields.values(), event_id))
                updated_event = cursor.fetchone()

                return updated_event
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.delete('/delete_event/{event_id}', name='Delete event by id')
def delete_event(event_id: int) -> dict[str, str]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute('DELETE FROM events WHERE id=%s RETURNING *', (event_id,))
                event = cursor.fetchone()

                if not event:
                    raise HTTPException(status_code=404, detail="Event not found")

                return {'message': f'Event {event_id} deleted successfully', 'deleted event info': f'{event}'}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
