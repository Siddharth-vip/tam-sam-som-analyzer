import logging
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.business import router as business_router
from app.api.calculation import router as calculation_router
from app.api.evidence import router as evidence_router
from app.api.orchestration import router as orchestration_router
from app.api.pipeline import router as pipeline_router
from app.config import settings

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tam_sam_som_analyzer")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API for AI-driven TAM/SAM/SOM Market Analysis and validation.",
    debug=settings.DEBUG,
)

# Parse CORS allowed origins
cors_origins: List[str] = (
    ["*"]
    if settings.CORS_ALLOW_ORIGINS == "*"
    else [origin.strip() for origin in settings.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors with structured responses."""
    errors = jsonable_encoder(exc.errors())
    logger.warning("Request validation error on %s %s: %s", request.method, request.url.path, errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": errors,
            "status": "error",
            "error_type": "ValidationError",
            "message": "Invalid request parameters",
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle standard HTTP exceptions with structured responses."""
    logger.warning("HTTP %d error on %s %s: %s", exc.status_code, request.method, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status": "error",
            "error_type": "HTTPException",
            "message": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions gracefully without exposing internal stack traces in production."""
    logger.exception("Unhandled server exception on %s %s: %s", request.method, request.url.path, str(exc))
    detail_message = str(exc) if settings.DEBUG else "An unexpected internal server error occurred."
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": detail_message,
            "status": "error",
            "error_type": "InternalServerError",
            "message": detail_message,
        },
    )


# Register API Routers
app.include_router(business_router, prefix="/api/v1")
app.include_router(evidence_router, prefix="/api/v1")
app.include_router(calculation_router, prefix="/api/v1")
app.include_router(pipeline_router, prefix="/api/v1")
app.include_router(orchestration_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def read_root() -> Dict[str, Any]:
    """Root endpoint for backward compatibility."""
    return {
        "status": "ok",
        "message": "TAM/SAM/SOM Analyzer API is running",
    }


@app.get("/health", tags=["Health"])
def health_check() -> Dict[str, Any]:
    """Structured health check endpoint for production observability and readiness."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "llm": {
            "provider": "ollama",
            "model": settings.OLLAMA_MODEL,
            "base_url": settings.OLLAMA_BASE_URL,
        },
        "search": {
            "provider": settings.SEARCH_PROVIDER,
        },
    }
