from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.event_router import event_router
from routers.channel_router import channel_router
from routers.algorithm_router import algorithm_router
from routers.authorization_router import authorization_router
from routers.pass_reset_routers import router as pass_reset_router

origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:8000"
]


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
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    new_app.include_router(authorization_router)
    new_app.include_router(algorithm_router)
    new_app.include_router(event_router)
    new_app.include_router(channel_router)
    new_app.include_router(pass_reset_router)

    return new_app


app = create_app()
