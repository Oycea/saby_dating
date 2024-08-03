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


def get_response(url, headers):
    response = requests.get(url=url, headers=headers)
    return response


@router.get("/chat")
def get_chat_page(request: Request, offset: int = 0, limit: int = 30):
    try:
        with get_database_connection() as conn:
            with conn.cursor() as cursor:

                cursor.execute("SELECT user_id, message, TO_CHAR(date, 'HH24:MI') as date FROM messages ORDER BY id DESC LIMIT %s OFFSET %s", (limit, offset))
                limited_result = cursor.fetchall()  # Возвращает кортеж user_id, message и date

                cursor.execute("SELECT message FROM messages")
                full_result = cursor.fetchall()
                full_result_len = len(full_result)  # Возвращает кол-во всех сообщений

                access_token = request.cookies.get("access_token")
                url = "http://127.0.0.1:8002/get_current_user"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                }
                user = get_response(url, headers).json()  # Получение информации об авторизованном юзере через access_token

                cursor.execute("SELECT image FROM users_images WHERE user_id = %s AND is_profile_image = TRUE", (user['id'],))
                profile_image_data = cursor.fetchone()

                profile_image_bytes = profile_image_data[0]  # Преобразование двоичного кода изображения в b64 и передача url
                image_type = imghdr.what(io.BytesIO(profile_image_bytes))
                profile_image_base64 = base64.b64encode(profile_image_bytes).decode('utf-8')
                profile_image = f"data:image/{image_type};base64,{profile_image_base64}"

                return templates.TemplateResponse("index.html", {"request": request,
                                                                 "limited_result": limited_result,
                                                                 "full_result_len": full_result_len,
                                                                 'user': user,
                                                                 'profile_image': profile_image})
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})



