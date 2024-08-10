from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse
from utils import log_file_path

logs_router = APIRouter(tags=['logs router'])


@logs_router.get('/logs', response_class=PlainTextResponse)
async def get_logs():
    try:
        with open(log_file_path, "r") as log_file:
            logs = log_file.read()
        return logs
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Log file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
