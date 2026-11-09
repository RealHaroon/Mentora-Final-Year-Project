import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import settings
from database import models  # noqa: F401 — registers models on Base before create_all
from database.session import Base, engine, run_additive_migrations
from ml_core.model_manager import ModelManager
from ml_core.registry import build_model_registry
from routers import auth, career, dashboard, exam, interview, learning, notifications, users
from services.rate_limit import limiter

if settings.debug:
    from routers import debug as debug_router

# Without this, every logger.info() call in ml_core/ (model load/unload,
# the memory watchdog's RAM snapshots) is silently swallowed — Python's
# root logger defaults to WARNING with no handler attached. Phase 6's
# definition-of-done explicitly wants these logs actually collected.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_additive_migrations()

    manager = ModelManager(models=build_model_registry())
    await manager.startup()
    app.state.model_manager = manager

    yield

    await manager.shutdown()


app = FastAPI(title="Mentora API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(exam.router)
app.include_router(career.router)
app.include_router(interview.router)
app.include_router(learning.router)
app.include_router(dashboard.router)
app.include_router(notifications.router)

if settings.debug:
    app.include_router(debug_router.router)


@app.get("/")
def root():
    return {"name": "Mentora API", "docs": "/docs"}
