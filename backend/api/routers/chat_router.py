import datetime
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from routers.session import open_conn

chat_router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, user_id: int, message: str, date: str, last_message_id: int):
        message_data = {
            "userId": user_id,
            "message": message,
            "date": date,
            "last_message_id": last_message_id
        }
        for connection in self.active_connections:
            await connection.send_text(json.dumps(message_data))


manager = ConnectionManager()


@chat_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            data_json = json.loads(data)
            message = data_json.get("message")
            user_id = data_json.get("userId")
            dialogue_id = data_json.get("dialogue_id")
            date = datetime.datetime.now().strftime("%H:%M")

            try:
                with open_conn() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "INSERT INTO messages(user_id, message, date, dialogue_id, is_deleted) VALUES(%s, %s, %s, %s, %s)",
                            (user_id, message, datetime.datetime.now(), dialogue_id, False))
                        cursor.execute("SELECT id FROM messages WHERE id = (SELECT MAX(id) FROM messages)")
                        last_message_id = cursor.fetchone()
            except Exception as ex:
                raise HTTPException(status_code=500, detail=str(ex))

            await manager.broadcast(user_id, message, date, last_message_id)

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@chat_router.get("/load_messages")
async def load_messages(dialogue_id, offset: int = 30, limit: int = 30):
    try:
        with open_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT user_id, message, TO_CHAR(date, 'HH24:MI') as date, id FROM messages WHERE dialogue_id = %s AND is_deleted = false ORDER BY id DESC LIMIT %s OFFSET %s",
                    (dialogue_id, limit, offset))
                result = cursor.fetchall()  # Возвращает кортеж user_id, message, date и id сообщения
                if result is None:
                    raise HTTPException(status_code=404, detail="Сообщения не найдены")
                return result
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@chat_router.put("/delete_message/{messageId}", name='delete_message')
def delete_message(messageId: int):
    try:
        with open_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE messages SET is_deleted = true WHERE id = %s", (messageId,))
                return {"detail": "Сообщение успешно удалено"}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@chat_router.put("/edit_message/{messageId}/{messageText}", name="edit_message")
def edit_message(messageId: int, messageText: str):
    try:
        with open_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE messages SET message = %s WHERE id = %s", (messageText, messageId))
                return {"detail": "Сообщение успешно изменено"}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
