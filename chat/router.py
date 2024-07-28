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

    # async def send_personal_message(self, message: str, websocket: WebSocket):
    #     await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)
            try:
                with get_database_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute('INSERT INTO messages(text) VALUES(%s)', (message,))
                        print(message)
            except Exception as ex:
                raise HTTPException(status_code=500, detail=str(ex))


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(f"{data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/load_messages")
async def load_messages(offset: int = 30, limit: int = 30):
    try:
        with get_database_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT "text" FROM messages ORDER BY id DESC LIMIT %s OFFSET %s', (limit, offset))
                text = cursor.fetchall()
                text_list = [row[0] for row in text]
                return text_list
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))

