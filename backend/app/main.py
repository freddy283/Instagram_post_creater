from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
import os

from app.config import settings
from app.database import init_db
from app.routers import auth, user, instagram, schedule, posts
from app.routers import video

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(
    title="Aureus API",
    version="2.0.0",
    docs_url="/api/docs" if settings.APP_ENV != "production" else None,
    redoc_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ───────────────────────────────────────────────────────────────────────
_origins = list(set(settings.origins_list or []))
if settings.APP_ENV != "production":
    _origins = list({*_origins,
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
        "http://localhost:8000", "http://127.0.0.1:8000",
    })

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

@app.on_event("startup")
async def startup():
    logger.info("Initialising database…")
    init_db()
    # Ensure video output directory exists
    os.makedirs(settings.VIDEOS_DIR, exist_ok=True)
    logger.info(f"Videos dir: {os.path.abspath(settings.VIDEOS_DIR)}")
    logger.info("Ready.")

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(instagram.router)
app.include_router(schedule.router)
app.include_router(posts.router)
app.include_router(video.router)

@app.get("/health")
def health():
    return {"status": "ok", "env": settings.APP_ENV, "version": "2.0.0"}
