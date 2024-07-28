from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from session import get_database_connection

router = APIRouter(
    prefix="",
    tags=["Pages"]
)


templates = Jinja2Templates(directory="templates")


@router.get("/chat")
def get_chat_page(request: Request, offset: int = 0, limit: int = 30):
    try:
        with get_database_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT "text" FROM messages ORDER BY id DESC LIMIT %s OFFSET %s', (limit, offset))
                limited_text = cursor.fetchall()
                limited_text_list = [row[0] for row in limited_text]
                cursor.execute('SELECT "text" FROM messages')
                full_text = cursor.fetchall()
                full_text_list = [row[0] for row in full_text]
                return templates.TemplateResponse("index.html", {"request": request, "limited_text_list": limited_text_list, "full_text_list": full_text_list})
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))

