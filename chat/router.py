import datetime
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from session import get_database_connection

router = APIRouter(
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

    async def broadcast(self, user_id: int, message: str, date: str):
        message_data = {
            "userId": user_id,
            "message": message,
            "date": date,
        }
        for connection in self.active_connections:
            await connection.send_text(json.dumps(message_data))


manager = ConnectionManager()


@router.websocket("/ws")
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
                with get_database_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "INSERT INTO messages(user_id, message, date, dialogue_id) VALUES(%s, %s, %s, %s)",
                            (user_id, message, datetime.datetime.now(), dialogue_id))
            except Exception as ex:
                raise HTTPException(status_code=500, detail=str(ex))

            await manager.broadcast(user_id, message, date)

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/load_messages")
async def load_messages(offset: int = 30, limit: int = 30):
    try:
        with get_database_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT user_id, message, TO_CHAR(date, 'HH24:MI') as date FROM messages ORDER BY id DESC LIMIT %s OFFSET %s",
                    (limit, offset))
                result = cursor.fetchall()  # Возвращает кортеж user_id, message и date
                return result
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
