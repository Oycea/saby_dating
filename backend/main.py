from fastapi import FastAPI

from routers.event_router import event_router
from routers.algorithm_router import algorithm_router
from routers.authorization_router import authorization_router
from routers.channel_router import channel_router


def create_app() -> FastAPI:
    """
    Create and configure an instance of the FastAPI application.
    """
    new_app = FastAPI(
        title='Sabytin',
        version='0.0.1a'
    )

    new_app.include_router(authorization_router)
    new_app.include_router(algorithm_router)
    new_app.include_router(event_router)
    new_app.include_router(channel_router)
    app.include_router(pass_reset_router)

    return new_app


app = create_app()
