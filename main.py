from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pages.router import router as router_pages
from chat.router import router as router_chat
from authorization.router import router as router_authorization

app = FastAPI(
    title="Жопа"
)


app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(router_pages)
app.include_router(router_chat)
app.include_router(router_authorization)
