from typing import Optional

import psycopg2
from fastapi import HTTPException, APIRouter
from pydantic import BaseModel
from routers.session import open_conn
from psycopg2.extras import RealDictCursor

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


@algorithm_router.get('/get_likes/{user_id}', name='Get likes from user by user_id')
def get_likes(user_id: int) -> list[int]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id_to FROM likes WHERE user_id_from=%s", (user_id,))
                likes = cursor.fetchall()
                if not likes:
                    raise HTTPException(status_code=404, detail="Likes not found")
                likes = [like[0] for like in likes]
                return likes
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.get('/get_dislikes/{user_id}', name='Get dislikes from user by user_id')
def get_dislikes(user_id: int) -> list[int]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id_to FROM dislikes WHERE user_id_from=%s", (user_id,))
                dislikes = cursor.fetchall()
                if not dislikes:
                    raise HTTPException(status_code=404, detail="Dislikes not found")
                dislikes = [dislike[0] for dislike in dislikes]
                return dislikes
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.get('/find_matches/{user_id}', name='Find matches for user by user_id')
def find_matches(user_id: int) -> list[int]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
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


@algorithm_router.post('/create_like/{user_like_from}/{user_like_to}', name='Create like')
def create_like(user_like_from: int, user_like_to: int) -> dict[str, int | list[int]]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO likes (user_id_from, user_id_to) VALUES(%s, %s) RETURNING *",
                               (user_like_from, user_like_to))
                new_likes = cursor.fetchone()
            if not new_likes:
                raise HTTPException(status_code=404, detail="user_like_from/user_like_to not found")
            return {'The like has been set': new_likes}
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=400, detail="The user has already been liked")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.post('/create_dislike/{user_dislike_from}/{user_dislike_to}', name='Create dislike')
def create_like(user_dislike_from: int, user_dislike_to: int) -> dict[str, int | list[int]]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO dislikes (user_id_from, user_id_to) VALUES(%s, %s) RETURNING *",
                               (user_dislike_from, user_dislike_to))
                new_dislikes = cursor.fetchone()
            if not new_dislikes:
                raise HTTPException(status_code=404, detail="user_dislike_from/user_dislike_to not found")
            return {'The dislike has been set': new_dislikes}
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=400, detail="The user has already been disliked")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.delete('/delete_all_likes/', name='Delete all likes')
def delete_all_likes() -> dict[str, str]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM likes")
                return {'message': 'the "like" table has been successfully cleared'}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.delete('/delete_all_dislikes/', name='Delete all dislikes')
def delete_all_dislikes() -> dict[str, str]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM dislikes")
                return {'message': 'the "dislike" table has been successfully cleared'}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.get('/list_questionnaires/{user_id}', name='list of assessment questionnaires')
def list_questionnaires(user_id_var: int) -> list[int]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                first_request = ("WITH tmp_interests AS( "
                                 "SELECT ui.user_id as id FROM "
                                 "( "
                                 "filters_interests as fi JOIN users_interests AS ui "
                                 "ON fi.interest_id = ui.interest_id "
                                 ")"
                                 "WHERE fi.user_id = %s AND ui.user_id <> %s), "
                                 " "
                                 "tmp_table AS "
                                 "( "
                                 "(SELECT id FROM users WHERE city = (SELECT city FROM filters WHERE user_id = %s) AND "
                                 "id <> %s) "
                                 " UNION ALL "
                                 "(SELECT id FROM users WHERE gender_id = (SELECT gender_id FROM filters WHERE user_id "
                                 "= %s) AND id <> %s) "
                                 " UNION ALL "
                                 "(SELECT id FROM users WHERE target_id = (SELECT target_id FROM filters WHERE user_id "
                                 "= %s) AND id <> %s) "
                                 " UNION ALL "
                                 "(SELECT id FROM users WHERE communication_id = (SELECT communication_id FROM filters "
                                 "WHERE user_id = %s) AND id <> %s) "
                                 " UNION ALL "
                                 "(SELECT id FROM users WHERE height BETWEEN (SELECT height_min FROM filters WHERE "
                                 "user_id = %s) AND (SELECT height_max FROM filters WHERE user_id = %s) AND id <> %s) "
                                 " UNION ALL "
                                 "(SELECT id FROM users WHERE date_part('YEAR', AGE(DATE(birthday))) BETWEEN (SELECT "
                                 "age_min FROM filters WHERE user_id = %s) AND (SELECT age_max FROM filters WHERE "
                                 "user_id = %s) AND id <> %s) "
                                 ") "
                                 " "
                                 "SELECT id "
                                 "FROM (SELECT id FROM tmp_interests UNION ALL SELECT id FROM tmp_table) "
                                 "GROUP BY id "
                                 "HAVING id NOT IN (SELECT user_id_to FROM likes WHERE user_id_from = %s) "
                                 "AND id NOT IN (SELECT user_id_to FROM dislikes WHERE user_id_from = %s) "
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
                    second_request = ("SELECT id FROM users WHERE id <> %s "
                                      "AND id NOT IN (SELECT user_id_to FROM likes WHERE user_id_from = %s) "
                                      "AND id NOT IN (SELECT user_id_to FROM dislikes WHERE user_id_from = %s) ")
                    sel_vars = (user_id_var, user_id_var, user_id_var)
                    cursor.execute(second_request, sel_vars)
                    all_questionnaires = cursor.fetchall()
                if not all_questionnaires:
                    raise HTTPException(status_code=404, detail="Questionnaires not found")
                all_questionnaires = [quest[0] for quest in all_questionnaires]
                return all_questionnaires
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.post('/create_filters/{user_id}',  name="create filters for user")
def create_filters(user_id: int, age_min: Optional[int] = None, age_max: Optional[int] = None,
                   height_min: Optional[int] = None, height_max: Optional[int] = None,
                   communication_id: Optional[int] = None, target_id: Optional[int] = None,
                   gender_id: Optional[int] = None, city: Optional[str] = None,
                   interests: Optional[list[int]] = []) -> dict[str,int]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
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

