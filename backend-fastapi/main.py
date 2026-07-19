from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from server.session import sessionmanager

from authentication.views import router as auth_router
from links.views import router as link_router
from server.limiter import limiter
from server import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    sessionmanager.init_db()
    yield
    await sessionmanager.close()


app = FastAPI(lifespan=lifespan, debug=settings.DEBUG)

os.makedirs(settings.BASE_UPLOAD_DIR, exist_ok=True)
app.mount(
    settings.UPLOAD_URL, StaticFiles(directory=settings.BASE_UPLOAD_DIR), name="media"
)
app.include_router(auth_router)
app.include_router(link_router)
origins = ["http://localhost:4200"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
