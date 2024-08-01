import psycopg2
from fastapi import HTTPException, APIRouter
from routers.session import open_conn

algorithm_router = APIRouter(prefix='/algorithm', tags=['Algorithm'])


@algorithm_router.get('/get_all_users/', name='Get all users')
def get_all_users() -> list[list]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
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
            return {'new line': new_likes}
    except psycopg2.IntegrityError as ex:
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
            return {'new line': new_dislikes}
    except psycopg2.IntegrityError as ex:
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


@algorithm_router.post('/list_questionnaires/{user_id}', name='list of assessment questionnaires')
def list_questionnaires(user_id_var: int, city_var: int, gender_var: int, age_min: int, age_max: int, height_min: int,
                        height_max: int,
                        interes_1: str, interes_2: str, interes_3: str, communication_id_var: int) -> list[list]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                frst_request = ("WITH creating_grand_selection as("
                                "(SELECT * FROM (SELECT * FROM users WHERE city=%s AND gender_id=%s AND date_part('year', age(timestamp birthday)) BETWEEN %s AND %s) WHERE height BETWEEN %s AND %s)"
                                "UNION"
                                "(SELECT * FROM (SELECT * FROM users WHERE city=%s AND gender_id=%s AND date_part('year', age(timestamp birthday)) BETWEEN %s AND %s) WHERE communication_id = %s)"
                                "UNION"
                                "(SELECT U.id as id, email, 'password', 'name', city, birthday, 'position', height, gender_id, target_id, communacation_id"
                                "FROM (users_interests JOIN interests ON users_interests.interests_id = interests.id) AS join_inters"
                                "JOIN (SELECT * FROM users WHERE city=%s AND gender_id=%s AND date_part('year', age(timestamp birthday)) BETWEEN %s AND %s) AS U ON join_inters.user_id = U.id"
                                "WHERE title =%s)"
                                "UNION"
                                "(SELECT U.id as id, email, 'password', 'name', city, birthday, 'position', height, gender_id, target_id, communacation_id"
                                "FROM (users_interests JOIN interests ON users_interests.interests_id = interests.id) AS join_inters"
                                "JOIN (SELECT * FROM users WHERE city=%s AND gender_id=%s AND date_part('year', age(timestamp birthday)) BETWEEN %s AND %s) AS U ON join_inters.user_id = U.id"
                                "WHERE title =%s)"
                                "UNION"
                                "(SELECT U.id as id, email, 'password', 'name', city, birthday, 'position', height, gender_id, target_id, communacation_id"
                                "FROM (users_interests JOIN interests ON users_interests.interests_id = interests.id) AS join_inters"
                                "JOIN (SELECT * FROM users WHERE city=%s AND gender_id=%s AND date_part('year', age(timestamp birthday)) BETWEEN %s AND %s) AS U ON join_inters.user_id = U.id"
                                "WHERE title =%s)"
                                ")"
                                "SELECT id"
                                "FROM creating_grand_selection"
                                "GROUP BY id"
                                "HAVING id NOT IN (SELECT user_id_to FROM likes WHERE user_like_from = %s)"
                                "AND id NOT IN (SELECT user_id_to FROM dislikes WHERE user_id_from = %s)"
                                "ORDER BY count(*) DESC"
                                )
                sel_vars = (
                    city_var, gender_var, age_min, age_max, height_min, height_max, city_var, gender_var, age_min,
                    age_max,
                    communication_id_var,
                    city_var, gender_var, age_min, age_max, interes_1, city_var, gender_var, age_min, age_max,
                    interes_2,
                    city_var, gender_var, age_min, age_max, interes_3, user_id_var, user_id_var)
                cursor.execute(find_matches, sel_vars)
                all_questionnaires = cursor.fetchall()
                if not all_questionnaires:
                    raise HTTPException(status_code=404, detail="Matches not found")
                return all_questionnaires
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
