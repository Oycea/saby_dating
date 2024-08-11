from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from utils import setup_logging


async def http_exception_handler(request: Request, exc: HTTPException):
    logger = setup_logging(request)
    logger.error(f"HTTPException: {exc.detail} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )
