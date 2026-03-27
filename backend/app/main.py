from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.logging import configure_logging
from app.services.bootstrap_service import initialize_application
from app.services.scheduler_service import configure_scheduler_from_settings, shutdown_scheduler, start_scheduler
from app.services.settings_service import get_settings
from app.db.session import SessionLocal


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    initialize_application()
    start_scheduler()
    with SessionLocal() as session:
        settings = get_settings(session)
        configure_scheduler_from_settings(settings.daily_run_time)
    yield
    shutdown_scheduler()


app = FastAPI(
    title="OncoWatch Local API",
    version="0.1.0",
    description="Local-first backend for OncoWatch",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "http://127.0.0.1:1420", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "app": "OncoWatch"}
