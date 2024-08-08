from datetime import datetime
from typing import Optional, List, Any, Dict
import psycopg2

from psycopg2.extras import RealDictCursor
from fastapi import HTTPException, APIRouter, Depends, File, UploadFile

from routers.session import open_conn
from routers.authorization_router import get_current_user, User

event_router = APIRouter(prefix='/events', tags=['Events'])


def check_creator(event_id: int, user_id: int) -> None:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT creator_id FROM events WHERE id=%s", (event_id,))
                creator_id = cursor.fetchone()
                if creator_id[0] != user_id:
                    raise HTTPException(status_code=401, detail="Could not validate credentials",
                                        headers={"WWW-Authenticate": "Bearer"})
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.get('/get_event/{event_id}', name='Get event by event_id')
def get_event(event_id: int) -> Dict[str, Any]:
    try:
        with open_conn() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM events WHERE id=%s", (event_id,))
                event = cursor.fetchone()

                if not event:
                    raise HTTPException(status_code=404, detail="Event not found")

                return event
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.get('/get_future_events', name='Get events that are not expired')
def get_future_events() -> Dict[str, int | List[Dict[str, Any]]]:
    try:
        with open_conn() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM events WHERE datetime>%s", (datetime.now(),))
                events = cursor.fetchall()

                if not events:
                    raise HTTPException(status_code=404, detail="No future events found")

                return {'size': len(events), 'events': events}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.get('/get_event_users/{event_id}', name='Get event users by event_id')
def get_event_users(event_id: int) -> Dict[str, int | List[int]]:
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
def get_event_tags(event_id: int) -> Dict[str, int | List[str]]:
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
def get_event_images(event_id: int) -> Dict[str, int | List[str]]:
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
def create_event(title: str,
                 description: str,
                 place: str,
                 tags: List[str],
                 date: datetime,
                 current_user: User = Depends(get_current_user),
                 users_limit: Optional[int] = None,
                 is_online: bool = False) -> Dict[str, str | Dict]:
    try:
        with open_conn() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                creator_id = current_user.id
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
                    tags_data.append((event['id'], tag_id['id']))
                cursor.executemany(tags_query + "(%s, %s);", tags_data)

                cursor.execute("INSERT INTO events_users (event_id, user_id) VALUES (%s, %s)",
                               (event['id'], creator_id))

                return {'message': f'Event with id {event["id"]} created successfully', 'event info': event}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.post('/add_user_to_the_event/{event_id}', name='Add user to the event by event_id')
def add_user_to_the_event(event_id: int, current_user: User = Depends(get_current_user)) -> Dict[str, int | List[int]]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                user_id = current_user.id
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
def add_tag_to_the_event(event_id: int, tag_title: str,
                         current_user: User = Depends(get_current_user)) -> Dict[str, int | List[str]]:
    try:
        check_creator(event_id, current_user.id)

        with open_conn() as connection:
            with connection.cursor() as cursor:
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


@event_router.post("/upload_event_image/{event_id}", name='Add image to the event by event_id')
async def upload_image(event_id: int, file: UploadFile = File(...),
                       current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    try:
        file_data = await file.read()
        check_creator(event_id, current_user.id)

        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO events_images (event_id, image) VALUES (%s, %s) RETURNING id",
                               (event_id, file_data))

                image_id = cursor.fetchone()

                if not image_id:
                    raise HTTPException(status_code=404, detail="No images or event found")

        return {"detail": f"Image with id {image_id[0]} successfully uploaded to the event {event_id}"}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.post('/add_tag/', name='Add tag')
def add_tag(tag_title: str) -> Dict[str, str]:
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
def edit_event_info(event_id: int,
                    title: Optional[str] = None,
                    description: Optional[str] = None,
                    place: Optional[str] = None,
                    date: Optional[datetime] = None,
                    users_limit: Optional[int] = None,
                    is_online: Optional[bool] = None,
                    current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        check_creator(event_id, current_user.id)

        with open_conn() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM events WHERE id=%s", (event_id,))
                event = cursor.fetchone()

                if not event:
                    raise HTTPException(status_code=404, detail="Event not found")

                update_fields = {
                    'title': title or event['title'],
                    'description': description or event['description'],
                    'place': place or event['place'],
                    'datetime': date or event['datetime'],
                    'users_limit': users_limit or event['users_limit'],
                    'is_online': is_online if is_online is not None else event['is_online']
                }

                cursor.execute(
                    "UPDATE events SET title=%s, description=%s, place=%s, datetime=%s, "
                    "users_limit=%s, is_online=%s WHERE id=%s RETURNING *",
                    (*update_fields.values(), event_id))
                updated_event = cursor.fetchone()

                return updated_event
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.delete('/delete_event/{event_id}', name='Delete event by event_id')
def delete_event(event_id: int, current_user: User = Depends(get_current_user)) -> Dict[str, str | Dict]:
    try:
        check_creator(event_id, current_user.id)

        with open_conn() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("DELETE FROM events WHERE id=%s RETURNING *", (event_id,))
                event = cursor.fetchone()

                if not event:
                    raise HTTPException(status_code=404, detail="Event not found")

                return {'message': f'Event {event_id} deleted successfully', 'deleted event info': event}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@event_router.delete('/delete_user_from_the_event/{event_id}/{user_id}',
                     name='Delete user from the event by event_id and user_id')
def delete_user_from_the_event(event_id: int, current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                user_id = current_user.id

                cursor.execute("SELECT creator_id FROM events WHERE id=%s", (event_id,))
                creator_id = cursor.fetchone()[0]
                if creator_id == user_id:
                    return {'message': f'Can not delete creator from users List'}

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
def delete_tag_from_the_event(event_id: int, tag_title: str,
                              current_user: User = Depends(get_current_user)) -> Dict[str, int | List]:
    try:
        check_creator(event_id, current_user.id)

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


@event_router.delete('/delete_image_from_the_event/{event_id}/{image_id}',
                     name='Delete image from the event by event_id and image_id')
def delete_image_from_the_event(event_id: int, image_id: int,
                                current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    try:
        check_creator(event_id, current_user.id)

        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM events_images WHERE id=%s AND event_id=%s RETURNING *",
                               (image_id, event_id))
                event_images = cursor.fetchone()

                if not event_images:
                    raise HTTPException(status_code=404, detail="Image not found in event")

                return {'message': f'Image {image_id} deleted from event {event_id} successfully'}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


# Функция поиска события
@event_router.get('/search_events/', name="search events to filters")
def search_events(title: Optional[str] = None, place: Optional[str] = None, is_online: Optional[bool] = None,
                  date_time: Optional[datetime] = None, tags: Optional[str] = None) -> dict[str, list[int]]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                list_events = []
                if tags is not None:  # Если тэги в фильтре присутствую, то они проверяются первыми
                    tags = tags.split(',')
                    for key in tags:
                        cursor.execute("SELECT events.id "
                                       "FROM events JOIN events_tags ON events.id = events_tags.event_id "
                                       "WHERE events_tags.tag_id = %s ", (key,))
                        sel_events = cursor.fetchall()
                        sel_events = [event[0] for event in sel_events]
                        if key == tags[0]:
                            list_events += sel_events
                        else:
                            list_events = [x for x in list_events if x in sel_events]
                    if not list_events:
                        raise HTTPException(status_code=404,
                                            detail="Events with these parameters were not found")
                        # Если по тэгам никаких совпадений нет, то конец
                if title is not None:
                    cursor.execute("SELECT id FROM events WHERE title = %s",
                                   (title,))  # Для каждого фильтра происходит поиск id ивента
                    events_by_title = cursor.fetchall()
                    events_by_title = [event[0] for event in events_by_title]
                    if not list_events:
                        list_events += events_by_title
                    else:
                        list_events = [x for x in list_events if
                                       x in events_by_title]
                        # В окончательный список ивентов попадут лишь те, которые совпали с предыдущими фильтрами
                if place is not None:
                    cursor.execute("SELECT id FROM events WHERE place = %s", (place,))
                    events_by_place = cursor.fetchall()
                    events_by_place = [event[0] for event in events_by_place]
                    if not list_events:
                        list_events += events_by_place
                    else:
                        list_events = [x for x in list_events if x in events_by_place]
                if is_online is not None:
                    cursor.execute("SELECT id FROM events WHERE is_online = %s", (is_online,))
                    events_by_is_online = cursor.fetchall()
                    events_by_is_online = [event[0] for event in events_by_is_online]
                    if not list_events:
                        list_events += events_by_is_online
                    else:
                        list_events = [x for x in list_events if x in events_by_is_online]
                if date_time is not None:
                    cursor.execute("SELECT id FROM events WHERE datetime = %s", (title,))
                    events_by_date_time = cursor.fetchall()
                    events_by_date_time = [event[0] for event in events_by_date_time]
                    if not list_events:
                        list_events += events_by_date_time
                    else:
                        list_events = [x for x in list_events if x in events_by_date_time]
                if not list_events:
                    raise HTTPException(status_code=404, detail="Events with these parameters were not found")
                return {"List of events with these parameters": list_events}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
