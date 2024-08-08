import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from routers.event_router import event_router
from routers.channel_router import channel_router
from routers.algorithm_router import algorithm_router
from routers.authorization_router import authorization_router
from routers.pass_reset_router import pass_reset_router
from routers.photos_router import photos_router
from routers.chat_router import chat_router
from routers.pages_router import pages_router
from utils import setup_scheduler
from exception_handlers import http_exception_handler


origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:8000",
    "http://localhost:80",
    "http://195.133.201.168",
    "http://195.133.201.168:80",
    "http://195.133.201.168:8000",
    "http://195.133.201.168:8080"
]

scheduler = setup_scheduler()

def create_app() -> FastAPI:
    """
    Create and configure an instance of the FastAPI application.
    """
    new_app = FastAPI(
        title='Sabytin',
        version='0.0.1a',
        # docs_url=None,
        # redoc_url=None
    )

    new_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Set-Cookie", "Access-Control-Allow-Headers", "Access-Control-Allow-Origin",
                       "Authorization"],
    )

    new_app.include_router(authorization_router)
    new_app.include_router(algorithm_router)
    new_app.include_router(event_router)
    new_app.include_router(channel_router)
    new_app.include_router(pass_reset_router)
    new_app.include_router(photos_router)
    new_app.include_router(chat_router)
    new_app.include_router(pages_router)
    new_app.add_exception_handler(HTTPException, http_exception_handler)

    return new_app


app = create_app()

