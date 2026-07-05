import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.config import settings

logger = structlog.get_logger()

_ALLOWED_ORIGINS = [
    origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()
]


def _attach_cors_headers(request: Request, response: JSONResponse) -> None:
    """Exception handlers registered for the bare Exception class run inside
    Starlette's ServerErrorMiddleware, which wraps *outside* CORSMiddleware --
    so a response from general_exception_handler never gets CORS headers
    from the middleware stack and the browser reports it as a network
    failure (TypeError: Failed to fetch) instead of surfacing the real 500.
    Attach them here directly as a workaround for that ordering."""
    origin = request.headers.get("origin")
    if origin and (origin in _ALLOWED_ORIGINS or "*" in _ALLOWED_ORIGINS):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    logger.warning(
        "HTTP exception occurred",
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        detail=exc.detail,
    )
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning(
        "Validation error occurred",
        path=request.url.path,
        method=request.method,
        errors=exc.errors(),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation failed", "details": exc.errors()},
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception occurred",
        path=request.url.path,
        method=request.method,
        error=str(exc),
    )
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"},
    )
    _attach_cors_headers(request, response)
    return response


def register_exception_handlers(app: FastAPI) -> None:
    """Centralized exception handling: never leak stack traces to the client."""
    # Starlette's add_exception_handler stub wants a handler typed to the
    # base Exception, but its runtime dispatch always passes the registered
    # exception subclass -- this is a known stub variance mismatch, not a
    # real type error (the equivalent @app.exception_handler(...) decorator
    # form hits the same mismatch).
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, general_exception_handler)
