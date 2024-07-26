from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from session import get_database_connection

router = APIRouter(
    prefix="/pages",
    tags=["Pages"]
)


templates = Jinja2Templates(directory="templates")


@router.get("/chat")
def get_chat_page(request: Request):
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT "text" FROM messages')
    text = cursor.fetchall()
    text_list = [row[0] for row in text]
    cursor.close()
    conn.close()
    return templates.TemplateResponse("index.html", {"request": request, "text": text_list})
    # conn = get_database_connection()
    # text = conn.fetch('SELECT "text" FROM messages')
    # text_list = [row['text'] for row in text]
    # conn.close()


@router.get('/get_chat_messages')
def get_chat_messages(request: Request):
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT "text" FROM messages')
    text = cursor.fetchall()
    text_list = [row[0] for row in text]
    cursor.close()
    conn.close()
    return templates.TemplateResponse('get_chat_messages.html', {"request": request, "text": text_list})
