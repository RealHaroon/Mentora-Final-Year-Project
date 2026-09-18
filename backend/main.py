from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import models  # noqa: F401 — registers models on Base before create_all
from database.session import Base, engine
from routers import auth, career, dashboard, exam, interview, learning, notifications, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Mentora API", lifespan=lifespan)

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


@app.get("/")
def root():
    return {"name": "Mentora API", "docs": "/docs"}
