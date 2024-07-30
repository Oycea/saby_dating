from fastapi import FastAPI
from routers.algorithm_router import algorithm_router


def create_app() -> FastAPI:
    """
    Create and configure an instance of the FastAPI application.
    """
    new_app = FastAPI(
        title='Sabytin',
        version='0.0.1a'
    )

    new_app.include_router(algorithm_router)
    

    return new_app


app = create_app()