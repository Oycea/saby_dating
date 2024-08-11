import imghdr
import base64
from io import BytesIO

from datetime import datetime
from typing import Optional

import psycopg2
from fastapi import HTTPException, APIRouter, Depends
from routers.session import open_conn
from psycopg2.extras import RealDictCursor
from routers.authorization_router import User, get_current_user

algorithm_router = APIRouter(prefix='/algorithm', tags=['Algorithm'])


@algorithm_router.get('/get_all_users/', name='Get all users')
def get_all_users() -> list[dict]:
    try:
        with open_conn() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM users")
                users = cursor.fetchall()
                if not users:
                    raise HTTPException(status_code=404, detail="Users not found")
                return users
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.get('/get_likes/', name='Get likes from user by user_id')
def get_likes(current_user: User = Depends(get_current_user)) -> list[dict]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                user_id = current_user.id
                cursor.execute(
                    "SELECT user_id_to, created_at FROM likes WHERE user_id_from=%s",
                    (user_id,))
                likes = cursor.fetchall()
                if not likes:
                    raise HTTPException(status_code=404, detail="Likes not found")
                likes = [like[0] for like in likes]
                return likes
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.get('/get_dislikes/', name='Get dislikes from user by user_id')
def get_dislikes(current_user: User = Depends(get_current_user)) -> list[int]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                user_id = current_user.id
                cursor.execute("SELECT user_id_to, created_at FROM dislikes WHERE user_id_from=% ", (user_id,))
                dislikes = cursor.fetchall()
                if not dislikes:
                    raise HTTPException(status_code=404, detail="Dislikes not found")
                dislikes = [dislike[0] for dislike in dislikes]
                return dislikes
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.get('/find_matches/', name='Find matches for user by user_id')
def find_matches(current_user: User = Depends(get_current_user)) -> list[int]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                user_id = current_user.id
                cursor.execute(
                    "SELECT user_id_to FROM likes WHERE user_id_to IN (SELECT user_id_from FROM likes WHERE "
                    "user_id_to=%s)",
                    (user_id,))
                matches = cursor.fetchall()
                if not matches:
                    raise HTTPException(status_code=404, detail="Matches not found")
                matches = [match[0] for match in matches]
                return matches
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.post('/create_like/{user_like_to}', name='Create like')  # Сделать проверку на существование диалога
def create_like(user_like_to: int, user_like_from:int) -> dict[str, int | list]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                #user_like_from = current_user.id
                cursor.execute(
                    "INSERT INTO likes (user_id_from, user_id_to, created_at) VALUES(%s, %s, NOW()::timestamp) "
                    "RETURNING *",
                    (user_like_from, user_like_to))
                new_likes = cursor.fetchone()
                if not new_likes:
                    raise HTTPException(status_code=404, detail="user_like_from/user_like_to not found")
                cursor.execute("SELECT * FROM likes WHERE user_id_from = %s AND user_id_to = %s",
                               (user_like_to, user_like_from,))
                new_match = cursor.fetchall()
                print(new_match)
                print(new_likes)
                if new_match:
                    cursor.execute(
                        "SELECT * FROM dialogues WHERE ((user1_id = %s AND user2_id = %s) OR (user1_id = %s AND "
                        "user2_id = %s)) AND is_deleted = false")
                    if not cursor.fetchall():
                        cursor.execute("INSERT INTO dialogues (user1_id, user2_id) VALUES(%s, %s)",
                                       (user_like_from, user_like_to))
                        return {"Match! A new dialog has been created!": [user_like_from, user_like_to]}
                    return {"The dialogue already exists, like has been set": [user_like_from, user_like_to]}
                else:
                    return {'The like has been set': new_likes}
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=400, detail="The user has already been liked")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.post('/create_dislike/{user_dislike_to}', name='Create dislike')
def create_dislike(user_dislike_to: int, current_user: User = Depends(get_current_user)) -> dict[str, int | list]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                user_dislike_from = current_user.id
                cursor.execute(
                    "INSERT INTO dislikes (user_id_from, user_id_to, created_at) VALUES(%s, %s, NOW()::timestamp) "
                    "RETURNING *",
                    (user_dislike_from, user_dislike_to))
                new_dislikes = cursor.fetchone()
                if not new_dislikes:
                    raise HTTPException(status_code=404, detail="user_dislike_from/user_dislike_to not found")
                return {'The dislike has been set': new_dislikes}
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=400, detail="The user has already been disliked")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.delete('/delete_all_likes/', name='Delete all likes')  # Функция не нужна
def delete_all_likes() -> dict[str, str]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM likes")
                return {'message': 'the "like" table has been successfully cleared'}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.delete('/delete_all_dislikes/', name='Delete all dislikes')  # Функция не нужна
def delete_all_dislikes() -> dict[str, str]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM dislikes")
                return {'message': 'the "dislike" table has been successfully cleared'}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.get('/list_questionnaires/', name='list of assessment questionnaires')
def list_questionnaires(current_user: User = Depends(get_current_user)) -> list[int]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                user_id_var = current_user.id
                first_request = ("WITH tmp_interests AS( "
                                 "SELECT ui.user_id as id FROM "
                                 "( "
                                 "filters_interests as fi JOIN users_interests AS ui "
                                 "ON fi.interest_id = ui.interest_id AND fi.is_deleted AND fi.is_deleted = false AND "
                                 "ui.is_deleted = false"
                                 ")"
                                 "WHERE fi.user_id = %s AND ui.user_id <> %s), "
                                 " "
                                 "tmp_table AS "
                                 "( "
                                 "(SELECT id FROM users WHERE city = (SELECT city FROM filters WHERE user_id = %s) AND "
                                 "id <> %s AND is_deleted = false) "
                                 " UNION ALL "
                                 "(SELECT id FROM users WHERE gender_id = (SELECT gender_id FROM filters WHERE user_id "
                                 "= %s) AND id <> %s AND is_deleted = false) "
                                 " UNION ALL "
                                 "(SELECT id FROM users WHERE target_id = (SELECT target_id FROM filters WHERE user_id "
                                 "= %s) AND id <> %s AND is_deleted = false) "
                                 " UNION ALL "
                                 "(SELECT id FROM users WHERE communication_id = (SELECT communication_id FROM filters "
                                 "WHERE user_id = %s) AND id <> %s AND is_deleted = false) "
                                 " UNION ALL "
                                 "(SELECT id FROM users WHERE height BETWEEN (SELECT height_min FROM filters WHERE "
                                 "user_id = %s) AND (SELECT height_max FROM filters WHERE user_id = %s) AND id <> %s "
                                 "AND is_deleted = false)"
                                 " UNION ALL "
                                 "(SELECT id FROM users WHERE date_part('YEAR', AGE(DATE(birthday))) BETWEEN (SELECT "
                                 "age_min FROM filters WHERE user_id = %s) AND (SELECT age_max FROM filters WHERE "
                                 "user_id = %s) AND id <> %s AND is_deleted = false) "
                                 ") "
                                 " "
                                 "SELECT id "
                                 "FROM (SELECT id FROM tmp_interests UNION ALL SELECT id FROM tmp_table) "
                                 "GROUP BY id "
                                 "HAVING id NOT IN (SELECT user_id_to FROM likes WHERE user_id_from = %s AND "
                                 "status_reaction(created_at) = true)"
                                 "AND id NOT IN (SELECT user_id_to FROM dislikes WHERE user_id_from = %s AND "
                                 "status_reaction(created_at) = true)"
                                 "ORDER BY count(*) DESC; "
                                 )
                sel_vars = (
                    user_id_var, user_id_var, user_id_var, user_id_var, user_id_var, user_id_var, user_id_var,
                    user_id_var,
                    user_id_var,
                    user_id_var, user_id_var, user_id_var, user_id_var, user_id_var, user_id_var, user_id_var,
                    user_id_var,
                    user_id_var)
                cursor.execute(first_request, sel_vars)
                all_questionnaires = cursor.fetchall()
                if not all_questionnaires:
                    second_request = ("SELECT id FROM users WHERE id <> %s AND is_deleted = false "
                                      "AND id NOT IN (SELECT user_id_to FROM likes WHERE user_id_from = %s AND "
                                      "status_reaction(created_at) = true)"
                                      "AND id NOT IN (SELECT user_id_to FROM dislikes WHERE user_id_from = %s AND "
                                      "status_reaction(created_at) = true) ")
                    sel_vars = (user_id_var, user_id_var, user_id_var)
                    cursor.execute(second_request, sel_vars)
                    all_questionnaires = cursor.fetchall()
                if not all_questionnaires:
                    raise HTTPException(status_code=404, detail="Questionnaires not found")
                all_questionnaires = [quest[0] for quest in all_questionnaires]
                return all_questionnaires
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.post('/create_filters/', name="create filters for user")
def create_filters(age_min: Optional[int] = None, age_max: Optional[int] = None,
                   height_min: Optional[int] = None, height_max: Optional[int] = None,
                   communication_id: Optional[int] = None, target_id: Optional[int] = None,
                   gender_id: Optional[int] = None, city: Optional[str] = None,
                   interests: Optional[list[int]] = [],
                   current_user: User = Depends(get_current_user)) -> dict[str, int]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                user_id = current_user.id
                filters_ins = ("INSERT INTO filters "
                               "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)")
                filt_vars = (user_id, age_min, age_max, height_min, height_max, communication_id, target_id,
                             gender_id, city)
                cursor.execute(filters_ins, filt_vars)
                for key in interests:
                    cursor.execute("INSERT INTO filters_interests VALUES(%s, %s)", (user_id, key))
                return {"filters have been added successfully": user_id}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.patch('/patch_filters/', name="patch filters for users search")
def patch_filters(age_min: Optional[int] = None, age_max: Optional[int] = None,
                  height_min: Optional[int] = None, height_max: Optional[int] = None,
                  communication_id: Optional[int] = None, target_id: Optional[int] = None,
                  gender_id: Optional[int] = None, city: Optional[str] = None,
                  interests: Optional[list[int]] = [],
                  current_user: User = Depends(get_current_user)) -> dict[str, int]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                user_id = current_user.id
                cursor.execute("SELECT * FROM filters WHERE user_id = %s and is_deleted = false ", (user_id,))
                search_filters = cursor.fetchone()
                if not search_filters:
                    raise HTTPException(status_code=404, detail="no filters were found for this user")
                new_filters = {
                    "user id": search_filters[0],
                    "age min": age_min or search_filters[1],
                    "age max": age_max or search_filters[2],
                    "height min": height_min or search_filters[3],
                    "height max": height_max or search_filters[4],
                    "communication id": communication_id or search_filters[5],
                    "target id": target_id or search_filters[6],
                    "gender id": gender_id or search_filters[7],
                    "city": city or search_filters[8]
                }
                print(new_filters)
                up_filters = ("UPDATE filters "
                              "SET user_id = %s, age_min = %s, age_max = %s, height_min = %s, height_max = %s, "
                              "communication_id = %s, "
                              "target_id = %s, gender_id = %s, city = %s "
                              "WHERE user_id = %s ")
                vars_filters = (
                    new_filters["user id"], new_filters["age min"], new_filters["age max"], new_filters["height min"],
                    new_filters["height max"], new_filters["communication id"], new_filters["target id"],
                    new_filters["gender id"], new_filters["city"], user_id,)
                cursor.execute(up_filters, vars_filters)
                if interests:
                    cursor.execute("DELETE FROM filters_interests WHERE user_id = %s ", (user_id,))
                    for key in interests:
                        cursor.execute("INSERT INTO filters_interests VALUES(%s, %s)", (user_id, key))
                return {"filters have been successfully updated for the user with the index": user_id}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.get('/search_events/', name="search events to filters")  # Добавить в events
def search_events(title: Optional[str] = None, place: Optional[str] = None, is_online: Optional[bool] = None,
                  date_time: Optional[datetime] = None, tags: Optional[str] = None) -> dict[str, list[int]]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                list_events = []
                if tags is not None:  # Если тэги в фильтре присутствую, то они проверяются первыми
                    tags = tags.split(',')
                    for key in tags:
                        cursor.execute("SELECT event_id "
                                       "FROM events_tags "
                                       "WHERE tag_id = %s AND is_deleted = false ", (key,))
                        # cursor.execute("SELECT events_tags.event_id "
                        #                "FROM events_tags JOIN tags ON events_tags.tag_id = tags.id "
                        #                "WHERE tags.title = %s ", (key, ))
                        sel_events = cursor.fetchall()
                        sel_events = [event[0] for event in sel_events]
                        if key == tags[0]:
                            list_events += sel_events
                        else:
                            list_events = [x for x in list_events if x in sel_events]
                    if not list_events:
                        raise HTTPException(status_code=404,
                                            detail="Events with these parameters were not found")  # Если по тэгам никаких совпадений нет, то конец
                if title is not None:
                    cursor.execute("SELECT id FROM events WHERE title = %s AND is_deleted = false ",
                                   (title,))  # Для каждого фильтра происходит поиск id ивента
                    events_by_title = cursor.fetchall()
                    events_by_title = [event[0] for event in events_by_title]
                    if not list_events:
                        list_events += events_by_title
                    else:
                        list_events = [x for x in list_events if
                                       x in events_by_title]  # В окончательный список ивентов попадут лишь те,которые совпали с предыдущими фильтрами
                if place is not None:
                    cursor.execute("SELECT id FROM events WHERE place = %s AND is_deleted = false ", (place,))
                    events_by_place = cursor.fetchall()
                    events_by_place = [event[0] for event in events_by_place]
                    if not list_events:
                        list_events += events_by_place
                    else:
                        list_events = [x for x in list_events if x in events_by_place]
                if is_online is not None:
                    cursor.execute("SELECT id FROM events WHERE is_online = %s AND is_deleted = false ", (is_online,))
                    events_by_is_online = cursor.fetchall()
                    events_by_is_online = [event[0] for event in events_by_is_online]
                    if not list_events:
                        list_events += events_by_is_online
                    else:
                        list_events = [x for x in list_events if x in events_by_is_online]
                if date_time is not None:
                    cursor.execute("SELECT id FROM events WHERE datetime = %s AND is_deleted = false ", (title,))
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


@algorithm_router.get('/search_dialog/', name="search dialog by name")  # Добавить в pages
def search_dialog(name_second_user: str, current_user: User = Depends(get_current_user)) -> dict[str, list[int]]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                main_user_id = current_user.id
                cursor.execute("SELECT dialogues.id "
                               "FROM dialogues JOIN users ON dialogues.user2_id = users.id "
                               "WHERE (dialogues.user1_id = %s AND users.name = %s  AND is_deleted = false ) ",
                               (main_user_id, name_second_user,))
                find_dialog = cursor.fetchall()
                cursor.execute("SELECT dialogues.id "
                               "FROM dialogues JOIN users ON dialogues.user1_id = users.id "
                               "WHERE (dialogues.user2_id = %s AND users.name = %s  AND is_deleted = false ) ",
                               (main_user_id, name_second_user,))
                find_dialog = find_dialog + cursor.fetchall()
                find_dialog = [dialog[0] for dialog in find_dialog]
                if not find_dialog:
                    raise HTTPException(status_code=404, detail="Dialog is not found")
                return {f"the dialog was successfully found with users by name{name_second_user}": find_dialog}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.get('/all_info/{user_id}', name="get all information about user")
def all_info(user_id: int) -> dict[str, list]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT name, city, date_part('YEAR', AGE(DATE(birthday))) as age, position, height, biography,  "
                    "(SELECT title FROM genders WHERE id = users.gender_id LIMIT 1) as gender, "
                    "(SELECT title FROM targets WHERE id = users.target_id LIMIT 1) as target, "
                    "(SELECT title FROM communications WHERE id = users.communication_id LIMIT 1) as communication "
                    "FROM users WHERE id = %s AND is_deleted = false", (user_id,))
                all_info_user = cursor.fetchone()
                cursor.execute("SELECT image FROM users_images WHERE user_id = %s and is_profile_image = false",
                               (user_id,))  # Не главные фото профиля
                other_img = cursor.fetchall()
                other_img = [img[0] for img in other_img]
                other_img = [base64.b64encode(photo).decode('utf-8') for photo in other_img]
                cursor.execute("SELECT image FROM users_images WHERE user_id = %s and is_profile_image = true",
                               (user_id,))  # Главное фото профиля
                main_img = cursor.fetchall()
                main_img = [img[0] for img in main_img]
                main_img = [base64.b64encode(photo).decode('utf-8') for photo in main_img]
                cursor.execute(
                    "SELECT interests.title FROM users_interests JOIN interests ON users_interests.interest_id = "
                    "interests.id WHERE users_interests.user_id = %s",
                    (user_id,))
                all_interests = cursor.fetchall()
                all_interests = [interest[0] for interest in all_interests]
                if not all_info_user:
                    raise HTTPException(status_code=404, detail="User is not found")
                return {"Information about user": all_info_user, "Profile image": main_img, "Other photos": other_img,
                        "All interests": all_interests}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
