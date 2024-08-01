from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pages.router import router as router_pages
from chat.router import router as router_chat
from authorization.router import router as router_authorization, RateLimitMiddleware

app = FastAPI(
    title="Жопа"
)


app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(RateLimitMiddleware, max_attempts=5, period=60)

app.include_router(router_pages)
app.include_router(router_chat)
app.include_router(router_authorization)

