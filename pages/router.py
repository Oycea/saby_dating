import base64
import imghdr
import io

from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse
from session import get_database_connection
from fastapi import HTTPException, Request, APIRouter
import requests

router = APIRouter(
    prefix="",
    tags=["Pages"]
)

templates = Jinja2Templates(directory="templates")


def get_response(access_token):
    url = "http://127.0.0.1:8000/get_current_user"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    response = requests.get(url=url, headers=headers)
    return response


def get_user_info_by_id(id):
    try:
        with get_database_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT name FROM users WHERE id = %s", (id,))
                name = cursor.fetchone()[0]

                profile_image = get_profile_image(id)

                return {"name": name, "profile_image": profile_image}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


def get_profile_image(id):
    try:
        with get_database_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT image FROM users_images WHERE user_id = %s AND is_profile_image = TRUE", (id,))
                profile_image_data = cursor.fetchone()

                profile_image_bytes = profile_image_data[
                    0]  # Преобразование двоичного кода изображения в b64 и передача url
                image_type = imghdr.what(io.BytesIO(profile_image_bytes))
                profile_image_base64 = base64.b64encode(profile_image_bytes).decode('utf-8')
                profile_image = f"data:image/{image_type};base64,{profile_image_base64}"

                return profile_image
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@router.get("/dialogues/{dialogue_id}", name='chat')  # Страница чата
def get_chat_page(dialogue_id: int, request: Request, offset: int = 0, limit: int = 30):
    try:
        with get_database_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT user_id, message, TO_CHAR(date, 'HH24:MI') as date FROM messages WHERE dialogue_id = %s ORDER BY id DESC LIMIT %s OFFSET %s",
                    (dialogue_id, limit, offset))
                limited_result = cursor.fetchall()  # Возвращает кортеж user_id, message и date

                cursor.execute("SELECT message FROM messages")
                full_result = cursor.fetchall()
                full_result_len = len(full_result)  # Возвращает кол-во всех сообщений

                access_token = request.cookies.get("access_token")
                self_user = get_response(
                    access_token).json()  # Получение информации об авторизованном юзере через access_token
                profile_image = get_profile_image(self_user['id'])

                cursor.execute("""
                                    SELECT 
                                        CASE 
                                            WHEN user1_id = %s THEN user2_id
                                            WHEN user2_id = %s THEN user1_id
                                        END
                                    FROM 
                                        dialogues
                                    WHERE 
                                        id = %s
                                """,
                               (self_user['id'], self_user['id'], dialogue_id))  # Возвращает id другого пользователя
                other_user_id = cursor.fetchone()[0]
                other_user = get_user_info_by_id(other_user_id)  # Возвращает имя и фото другого пользователя

                return templates.TemplateResponse("index.html", {"request": request,
                                                                 "limited_result": limited_result,
                                                                 "full_result_len": full_result_len,
                                                                 'self_user': self_user,
                                                                 'profile_image': profile_image,
                                                                 'other_user': other_user,
                                                                 'dialogue_id': dialogue_id})
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/dialogues")
def get_dialogues_page(request: Request):
    try:
        with get_database_connection() as conn:
            with conn.cursor() as cursor:
                access_token = request.cookies.get("access_token")
                self_user = get_response(access_token).json()
                cursor.execute("""
                                    SELECT 
                                        id AS dialogue_id,
                                        CASE 
                                            WHEN user1_id = %s THEN user2_id
                                            WHEN user2_id = %s THEN user1_id
                                        END
                                    FROM 
                                        dialogues
                                    WHERE 
                                        user1_id = %s OR user2_id = %s
                                """, (self_user['id'], self_user['id'], self_user['id'], self_user['id']))
                dialogues = cursor.fetchall()  # Возвращает id диалога и id всех собеседников пользователя

                other_user = []
                for dialogue in dialogues:
                    user_info = get_user_info_by_id(dialogue[1])  # Получаем имя и фото всех собеседников
                    other_user += [user_info]

                return templates.TemplateResponse("dialogues.html", {"request": request, "dialogues": dialogues,
                                                                     "other_user": other_user})
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
