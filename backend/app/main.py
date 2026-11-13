from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import update

from app import db
from app.config import settings
from app.models import Video, VideoStatus, init_db
from app.routers import health, llm, prompting, transcript, videos


def recover_interrupted_jobs() -> None:
    with db.SessionLocal() as session:
        session.execute(
            update(Video)
            .where(Video.status.in_([VideoStatus.PENDING, VideoStatus.PROCESSING]))
            .values(status=VideoStatus.FAILED, error="Server restarted during processing, retry")
        )
        session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    recover_interrupted_jobs()
    yield


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(llm.router, prefix="/api")
app.include_router(prompting.router, prefix="/api")
app.include_router(transcript.router, prefix="/api")
app.include_router(videos.router, prefix="/api")
