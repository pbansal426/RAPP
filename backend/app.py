from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.database import engine
from backend.core.exceptions import register_exception_handlers
from backend.core.logging import configure_logging
from backend.core.models import Base
from backend.routers import (
    auth,
    diagnose,
    payments,
    repair,
    repairs,
    vehicle_safety,
    vin,
)

configure_logging(settings)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    logger.info(
        "Starting up FastAPI application", port=settings.port, debug=settings.debug
    )
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("Shutting down FastAPI application")


app = FastAPI(
    title="RAPP Backend API Server",
    version="0.1.0",
    lifespan=lifespan,
)

allowed_origins_list = [
    origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list if allowed_origins_list else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(vin.router)
app.include_router(diagnose.router)
app.include_router(repair.router)
app.include_router(payments.router)
app.include_router(auth.router)
app.include_router(repairs.router)
app.include_router(vehicle_safety.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
