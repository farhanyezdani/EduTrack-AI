import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app import cache
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import auth, dashboard, model, students
from app.seed import ensure_users
from app.services.predictor import get_predictor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("edutrack")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    if settings.seed_demo_users:
        with SessionLocal() as db:
            ensure_users(db)
    predictor = get_predictor()
    log.info("Model %s loaded (threshold %.2f), cache: %s",
             predictor.version, predictor.threshold, cache.status())
    yield


app = FastAPI(title="EduTrack AI API", version="3.0.0", lifespan=lifespan,
              description="Student progress tracking and ML-based dropout risk prediction")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    log.info("%s %s -> %s (%.0f ms)", request.method, request.url.path,
             response.status_code, (time.perf_counter() - start) * 1000)
    return response


app.include_router(auth.router)
app.include_router(students.router)
app.include_router(dashboard.router)
app.include_router(model.router)


@app.get("/api/health", tags=["health"])
def health():
    p = get_predictor()
    return {"status": "ok", "model_version": p.version, "cache": cache.status(),
            "llm": "configured" if settings.llm_base_url and settings.llm_api_key else "rules-fallback"}
