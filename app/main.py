import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.logging import setup_logging, request_id_ctx
from app.core.redis import close_redis
from app.services import (
    TemplateValidationError,
    RateLimitExceededError,
    IdempotencyLockError,
    IdempotencyPayloadConflictError,
)

# Configure structured logs
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    # Startup tasks
    logger.info("Initializing Notification Service Application...")
    yield
    # Shutdown tasks
    logger.info("Shutting down Notification Service Application...")
    await close_redis()

app = FastAPI(
    title="Notification Service Backend API",
    description="A production-grade multi-channel notification microservice.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Middleware: Request tracing and performance monitoring
@app.middleware("http")
async def tracing_middleware(request: Request, call_next: Any) -> Response:
    # Generate or extract request correlation ID
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request_id_ctx.set(request_id)
    
    start_time = time.time()
    logger.info(
        f"HTTP Request: {request.method} {request.url.path}",
        extra={"method": request.method, "path": request.url.path}
    )
    
    try:
        response: Response = await call_next(request)
    except Exception as exc:
        # Catch errors occurring during response execution
        duration = time.time() - start_time
        logger.error(
            f"HTTP Request Failed: {request.method} {request.url.path} - Exception: {str(exc)}",
            extra={"method": request.method, "path": request.url.path, "duration_seconds": duration}
        )
        raise exc

    duration = time.time() - start_time
    logger.info(
        f"HTTP Response: {request.method} {request.url.path} - Status: {response.status_code}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_seconds": duration,
        }
    )
    
    response.headers["x-request-id"] = request_id
    return response

# Custom Exception Handler: Template rendering errors (HTTP 400)
@app.exception_handler(TemplateValidationError)
async def template_validation_error_handler(
    request: Request, exc: TemplateValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "TEMPLATE_VALIDATION_ERROR",
                "message": str(exc),
            }
        },
    )

# Custom Exception Handler: Rate limits (HTTP 429)
@app.exception_handler(RateLimitExceededError)
async def rate_limit_error_handler(
    request: Request, exc: RateLimitExceededError
) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(exc.retry_after)},
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": str(exc),
            }
        },
    )

# Custom Exception Handler: Concurrent Idempotency locks (HTTP 409)
@app.exception_handler(IdempotencyLockError)
async def idempotency_lock_error_handler(
    request: Request, exc: IdempotencyLockError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "IDEMPOTENCY_LOCK_IN_PROGRESS",
                "message": str(exc),
            }
        },
    )

# Custom Exception Handler: Idempotency payload mismatch (HTTP 409)
@app.exception_handler(IdempotencyPayloadConflictError)
async def idempotency_payload_conflict_handler(
    request: Request, exc: IdempotencyPayloadConflictError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "IDEMPOTENCY_PAYLOAD_CONFLICT",
                "message": str(exc),
            }
        },
    )

# Custom Exception Handler: Request validation failures (HTTP 400)
@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    message = "Request validation failed."
    if errors:
        # Produce a human-readable validation summary
        err_detail = errors[0]
        message = f"Validation failed: Field '{err_detail['loc'][-1]}' {err_detail['msg']}"
        
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "BAD_REQUEST",
                "message": message,
                "details": errors,
            }
        },
    )

# Custom Exception Handler: Starlette HTTPExceptions (HTTP 4xx/5xx)
@app.exception_handler(StarletteHTTPException)
async def starlette_http_error_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
            }
        },
    )

# Custom Exception Handler: General unhandled errors (HTTP 500)
@app.exception_handler(Exception)
async def general_unhandled_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception("An unhandled server exception occurred during request execution")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred on the server.",
            }
        },
    )

# Mount aggregated routes
app.include_router(api_router)
