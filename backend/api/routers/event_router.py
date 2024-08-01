from datetime import datetime
from typing import Optional, List
import psycopg2

from fastapi import HTTPException, APIRouter, Depends

from routers.session import open_conn
from routers.authorization_router import get_current_user

event_router = APIRouter(prefix='/events', tags=['Events'])


@event_router.get('/get_event/{event_id}', name='Get event by event_id')
def get_event(event_id: int) -> list:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM events WHERE id=%s", (event_id,))
                event = cursor.fetchone()
                if not event:
                    raise HTTPException(status_code=404, detail="Event not found")
                return event
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.get('/get_future_events', name='Get events that are not expired')
def get_future_events() -> dict[str, int | list]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM events WHERE datetime>%s", (datetime.now(),))
                events = cursor.fetchall()

                if not events:
                    raise HTTPException(status_code=404, detail="No future events found")

                return {'size': len(events), 'events': events}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.get('/get_event_users/{event_id}', name='Get event users by event_id')
def get_event_users(event_id: int) -> dict[str, int | list[int]]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id FROM events_users WHERE event_id=%s", (event_id,))
                users_data = cursor.fetchall()

                if not users_data:
                    raise HTTPException(status_code=404, detail="Users or event not found")

                users_id = [user[0] for user in users_data]
                return {'size': len(users_id), 'users ids': users_id}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.get('/get_event_tags/{event_id}', name='Get event tags by event_id')
def get_event_tags(event_id: int) -> dict[str, int | list[str]]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT t.title FROM "
                    "tags t JOIN events_tags et "
                    "ON t.id = et.tag_id WHERE et.event_id=%s",
                    (event_id,))
                tags_data = cursor.fetchall()

                if not tags_data:
                    raise HTTPException(status_code=404, detail="Tags or event not found")

                tags = [tags[0] for tags in tags_data]

                return {'size': len(tags), 'tags': tags}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.get('/get_event_images/{event_id}', name='Get event images by event_id')
def get_event_images(event_id: int) -> dict[str, int | list[str]]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT url FROM events_images WHERE event_id=%s", (event_id,))
                images_data = cursor.fetchall()

                if not images_data:
                    raise HTTPException(status_code=404, detail="Tags or event not found")

                images_urls = [images[0] for images in images_data]

                return {'size': len(images_urls), 'images urls': images_urls}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.post('/create_event/', name='Create new event')
def create_event(title: str, description: str, place: str, tags: List[str],
                 date: datetime, creator_id: int, images_url: Optional[List[str]] = None,
                 users_limit: Optional[int] = None, is_online: bool = False) -> dict[str, str | list]:
    # user_data = get_current_user(token)
    # creator_id = user_data.id
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "WITH new_event AS("
                    "INSERT INTO events (title, description, place, created_at, datetime, creator_id, users_limit, "
                    "is_online) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                    "RETURNING *)"
                    "SELECT * FROM new_event",
                    (title, description, place, datetime.now(), date, creator_id, users_limit, is_online))
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

                return {'message': f'Event with id {event[0]} created successfully', 'event info': event}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.post('/add_user_to_the_event/{event_id}/{user_id}', name='Add user to the event by event_id and user_id')
def add_user_to_the_event(event_id: int) -> dict[str, int | list[int]]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO events_users (event_id, user_id) VALUES (%s, %s)", (event_id, user_id))

                cursor.execute("SELECT user_id FROM events_users WHERE event_id=%s", (event_id,))
                events_users = cursor.fetchall()

                if not events_users:
                    raise HTTPException(status_code=404, detail="No users found for the event")

                users_id = [user[0] for user in events_users]
                return {'size': len(users_id), 'events_users': users_id}
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=400, detail="User already added to the event or invalid event/user ID")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.post('/add_tag_to_the_event/{event_id}/{tag_title}', name='Add tag to the event by event_id')
def add_tag_to_the_event(event_id: int, tag_title: str) -> dict[str, int | list[str]]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT creator_id FROM events WHERE id=%s", (event_id,))
                if creator_id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Could not validate credentials",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                # Получение id тега по его названию
                cursor.execute("SELECT id FROM tags WHERE title=%s", (tag_title,))
                tag_id_row = cursor.fetchone()
                if not tag_id_row:
                    raise HTTPException(status_code=404, detail="Tag not found")

                tag_id = tag_id_row[0]

                # Добавление тега к событию
                cursor.execute("INSERT INTO events_tags (event_id, tag_id) VALUES (%s, %s)", (event_id, tag_id))

                # Получение всех тегов для события
                cursor.execute(
                    "SELECT t.title FROM "
                    "tags t JOIN events_tags et "
                    "ON t.id = et.tag_id WHERE et.event_id=%s",
                    (event_id,))
                tags_data = cursor.fetchall()

                if not tags_data:
                    raise HTTPException(status_code=404, detail="No tags found for the event")

                tags = [tag[0] for tag in tags_data]

                return {'size': len(tags), 'event tags': tags}
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=400, detail="Tag already added to the event or invalid tag_title/event_id")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.post('/add_image_to_the_event/{event_id}/', name='Add images to the event by event_id')
def add_image_to_the_event(event_id: int, images_url: list[str]) -> dict[str, int | list[str]]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                if images_url:
                    images_query = "INSERT INTO events_images (event_id, url) VALUES "
                    images_data = [(event_id, url) for url in images_url]
                    cursor.executemany(images_query + "(%s, %s);", images_data)
                else:
                    raise HTTPException(status_code=400, detail="Nothing to add")

                cursor.execute("SELECT url FROM events_images WHERE event_id=%s", (event_id,))
                event_images = cursor.fetchall()

                if not event_images:
                    raise HTTPException(status_code=404, detail="No images found for the event")

                event_images = [image[0] for image in event_images]
                return {'size': len(event_images), 'event_images': event_images}
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=400, detail="Image already added to the event or invalid image/event ID")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.post('/add_tag/', name='Add tag')
def add_tag(tag_title: str) -> dict[str, str]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                # Добавление тега
                cursor.execute("INSERT INTO tags (title) VALUES (%s) RETURNING id", (tag_title,))
                tag_id = cursor.fetchone()

                return {'message': f'Tag {tag_title} with id {tag_id[0]} added successfully'}
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=400, detail="Tag already added to the tags")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.put('/edit_event_info/{event_id}/', name='Edit event by event_id')
def edit_event_info(event_id: int, title: Optional[str] = None,
                    description: Optional[str] = None,
                    place: Optional[str] = None,
                    date: Optional[datetime] = None, creator_id: Optional[int] = None,
                    users_limit: Optional[int] = None, is_online: Optional[bool] = None) -> list:
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
                    'is_online': is_online if is_online is not None else event[8]
                }

                cursor.execute(
                    "UPDATE events SET title=%s, description=%s, place=%s, datetime=%s, creator_id=%s, "
                    "users_limit=%s, is_online=%s WHERE id=%s RETURNING *",
                    (*update_fields.values(), event_id))
                updated_event = cursor.fetchone()

                return updated_event
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.delete('/delete_event/{event_id}', name='Delete event by event_id')
def delete_event(event_id: int) -> dict[str, str]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM events WHERE id=%s RETURNING *", (event_id,))
                event = cursor.fetchone()

                if not event:
                    raise HTTPException(status_code=404, detail="Event not found")

                return {'message': f'Event {event_id} deleted successfully', 'deleted event info': event}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.delete('/delete_user_from_the_event/{event_id}/{user_id}',
                     name='Delete user from the event by event id and user id')
def delete_user_from_the_event(event_id: int, user_id: int) -> dict[str, str]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT creator_id FROM events WHERE id=%s", (event_id,))
                creator_id = cursor.fetchone()[0]
                if creator_id == user_id:
                    return {'message': f'Can not delete creator from users list'}

                cursor.execute("DELETE FROM events_users WHERE event_id=%s AND user_id=%s RETURNING *",
                               (event_id, user_id))
                event_user = cursor.fetchone()

                if not event_user:
                    raise HTTPException(status_code=404, detail="User not found in event")

                return {'message': f'User {user_id} deleted from event {event_id} successfully'}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.delete('/delete_tag_from_the_event/{event_id}/{tag_title}',
                     name='Delete tag from the event by event_id')
def delete_tag_from_the_event(event_id: int, tag_title: str) -> dict[str, int | list]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                # Получение id тега по его названию
                cursor.execute("SELECT id FROM tags WHERE title=%s", (tag_title,))
                tag_id_row = cursor.fetchone()
                if not tag_id_row:
                    raise HTTPException(status_code=404, detail="Tag not found")

                tag_id = tag_id_row[0]

                # Удаление тега из события
                cursor.execute("DELETE FROM events_tags WHERE event_id=%s AND tag_id=%s RETURNING *",
                               (event_id, tag_id))
                deleted_tag = cursor.fetchone()

                if not deleted_tag:
                    raise HTTPException(status_code=404, detail="Tag not found in the event")

                # Получение всех оставшихся тегов для события
                cursor.execute(
                    "SELECT t.title FROM tags t JOIN events_tags et ON t.id = et.tag_id WHERE et.event_id=%s",
                    (event_id,))
                tags_data = cursor.fetchall()

                tags = [tag[0] for tag in tags_data]

                return {'size': len(tags), 'event tags': tags}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
