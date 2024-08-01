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

    async def broadcast(self, user_id: int, message: str):
        message_data = {
            "userId": user_id,
            "message": message
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

            try:
                with get_database_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("INSERT INTO messages(user_id, message) VALUES(%s, %s)", (user_id, message))
            except Exception as ex:
                raise HTTPException(status_code=500, detail=str(ex))

            await manager.broadcast(user_id, message)

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/load_messages")
async def load_messages(offset: int = 30, limit: int = 30):
    try:
        with get_database_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT user_id, message FROM messages ORDER BY id DESC LIMIT %s OFFSET %s", (limit, offset))
                text = cursor.fetchall()  # Возвращает кортеж user_id и message
                return text
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))

