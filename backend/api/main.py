from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from routers.chat_router import chat_router
from routers.pages_router import pages_router
from routers.authorization_router import authorization_router, RateLimitMiddleware

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
        RateLimitMiddleware, max_attempts=5, period=60,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory="static"), name="static")

    new_app.include_router(chat_router)
    new_app.include_router(pages_router)
    new_app.include_router(authorization_router)

    return new_app


app = create_app()
