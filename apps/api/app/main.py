from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.response import envelope
from app.core.database import SessionLocal
from app.db.seed import seed_defaults
from app.routers.auth_router import router as auth_router
from app.routers.health_router import router as health_router
from app.routers.search_router import router as search_router


configure_logging()
logger = get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    logger.info("api_startup", env=settings.env, database_url=settings.database_url)
    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.replace("sqlite:///", "")
        if not db_path:
            logger.warning("db_path_missing")
        elif not Path(db_path).exists():
            logger.warning("db_missing_run_migrations", db_path=db_path)
    if settings.auto_seed:
        with SessionLocal() as db:
            result = seed_defaults(db, settings)
            logger.info("seed_defaults", **result)
    yield


app = FastAPI(title="LetterOps API", version="0.1.0", lifespan=lifespan)

app.include_router(health_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope(data=None, error={"message": exc.detail}),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=envelope(data=None, error={"message": "Validation error", "details": exc.errors()}),
    )
