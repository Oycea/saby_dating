from fastapi import FastAPI

from routers.user_router import user_router
from routers.event_router import event_router


def create_app() -> FastAPI:
    new_app = FastAPI(
        title='Sabytin',
        version='0.0.1a'
    )

    new_app.include_router(user_router)
    new_app.include_router(event_router)

    return new_app


app = create_app()
