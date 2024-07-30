from typing import List

import psycopg2
from fastapi import HTTPException, APIRouter
from routers.session import open_conn

algorithm_router = APIRouter(prefix='/alorithm', tags=['Algorithm'])


@algorithm_router.get('/get_all_users/', name='get all users')
def get_all_users() -> list:
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


@algorithm_router.get('/get_likes/{user_id}', name='get likes')
def get_likes(user_id: int) -> list[int]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id_to FROM likes WHERE user_id_from=%s", (user_id,))
                likes = cursor.fetchall()
                if not likes:
                    raise HTTPException(status_code=404, detail="Likes not found")
                return likes
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.get('/get_dislikes/{user_id}', name='get dislikes')
def get_dislikes(user_id: int) -> list[int]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id_to FROM dislikes WHERE user_id_from=%s", (user_id,))
                dislikes = cursor.fetchall()
                if not dislikes:
                    raise HTTPException(status_code=404, detail="Dislikes not found")
                return dislikes
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.get('/find_matches/{user_id}', name='find matches')
def find_matches(user_id: int) -> list[int]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT user_id_to FROM likes WHERE user_id_to IN (SELECT user_id_from FROM likes WHERE user_id_to=%s)",
                    (user_id,))
                mathes = cursor.fetchall()
                if not mathes:
                    raise HTTPException(status_code=404, detail="Matches not found")
                return mathes
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.post('/create_like/{user_like_from}/{user_like_to}', name='create_like')
def create_like(user_like_from: int, user_like_to: int) -> dict[str, int | List[int]]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO likes (user_id_from, user_id_to) VALUES(%s, %s)",
                               (user_like_from, user_like_to))
                all_likes = cursor.fetchall()
            if not all_likes:
                raise HTTPException(status_code=404, detail="user_like_from/user_like_to not found")
            likes_to_user = [x[1] for x in all_likes]
            return {'size': len(all_likes), f'likes to user{user_like_from}': likes_to_user}
    except psycopg2.IntegrityError as ex:
        raise HTTPException(status_code=400, detail="The user has already been liked")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.post('/create_dislike/{user_dislike_from}/{user_dislike_to}', name='create_dislike')
def create_like(user_dislike_from: int, user_dislike_to: int) -> dict[str, int]:
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO dislikes (user_id_from, user_id_to) VALUES(%s, %s)",
                               (user_dislike_from, user_dislike_to))
                all_dislikes = cursor.fetchall()
            if not all_dislikes:
                raise HTTPException(status_code=404, detail="user_dislike_from/user_dislike_to not found")
            dislikes_to_user = [x[1] for x in all_dislikes]
            return {'size': len(all_dislikes), f'likes to user{user_dislike_from}': dislikes_to_user}
    except psycopg2.IntegrityError as ex:
        raise HTTPException(status_code=400, detail="The user has already been disliked")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.delete('/delete_likes/', name='delete likes')
def delete_likes():
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM likes")
                return {'message': 'the "like" table has been successfully cleared'}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@algorithm_router.delete('/delete_dislikes/', name='delete dislikes')
def delete_dislikes():
    try:
        with open_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM dislikes")
                return {'message': 'the "dislike" table has been successfully cleared'}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
