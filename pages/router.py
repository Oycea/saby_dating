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

                cursor.execute("SELECT user_id, message FROM messages ORDER BY id DESC LIMIT %s OFFSET %s", (limit, offset))
                limited_text_list = cursor.fetchall()  # Возвращает кортеж user_id и message
                cursor.execute('SELECT "message" FROM messages')
                full_text = cursor.fetchall()
                full_text_list = [row[0] for row in full_text]  # Возвращает полный список сообщений(текст)

                access_token = request.cookies.get("access_token")
                url = "http://127.0.0.1:8000/get_current_user"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                }
                user = get_response(url, headers).json()  # Получение информации об авторизованном юзере через access_token

                return templates.TemplateResponse("index.html", {"request": request,
                                                                 "limited_text_list": limited_text_list,
                                                                 "full_text_list": full_text_list,
                                                                 'user': user})
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})



