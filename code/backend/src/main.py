"""
Research Copilot - Enterprise FastAPI Application
"""
import logging
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from prometheus_client import make_asgi_app
import time

from .config import settings
from .database import create_tables
from .middlewares import setup_middlewares
from .routers import api_router
from .models import user, role, audit, paper, refresh_token
from .services.cache import RedisCache
from .services.opensearch import OpenSearchService
from .services.monitoring import performance_monitor
from .services.langfuse.factory import make_langfuse_tracer
from .services.audit import audit_service
from .utils.logging import setup_logging
from .utils.tracing import set_tracing_context, extract_tracing_from_request

# Setup structured logging
setup_logging()

# Create logger
logger = structlog.get_logger(__name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    logger.info("Starting Research Copilot application")

    # Initialize services
    try:
        # Create database tables
        await create_tables()

        # Initialize Redis cache
        # try:
        #     cache = RedisCache()
        #     await cache.connect()
        #     logger.info("Redis cache initialized")
        # except Exception as e:
        #     logger.warning("Redis cache initialization failed, continuing without cache", error=str(e))

        # # Initialize OpenSearch
        # try:
        #     opensearch = OpenSearchService()
        #     await opensearch.connect()
        #     logger.info("OpenSearch initialized")
        # except Exception as e:
        #     logger.warning("OpenSearch initialization failed, continuing without search", error=str(e))

        # Start audit service background worker
        await audit_service.start_background_worker()
        logger.info("Audit service background worker started")

        # logger.info("Services initialization completed")

    except Exception as e:
        logger.error("Failed to initialize critical services", error=str(e))
        raise

    yield

    # Stop audit service background worker
    await audit_service.stop_background_worker()

    # Cleanup
    logger.info("Shutting down Research Copilot application")

def create_application():
    """Create and configure the FastAPI application"""
    # Initialize Langfuse tracer
    try:
        langfuse_tracer = make_langfuse_tracer()
    except Exception as e:
        logger.warning("Langfuse tracer initialization failed, continuing without tracing", error=str(e))
        langfuse_tracer = None

    # Create FastAPI application
    app = FastAPI(
        title=settings.app_name,
        description="Enterprise-grade Research Copilot system with OpenRouter DeepSeek integration",
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # Add Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if settings.environment == "development" else ["yourdomain.com"]
    )

    # Rate limiting middleware
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Custom middlewares
    setup_middlewares(app)

    # Add Langfuse tracer to app state
    app.state.langfuse_tracer = langfuse_tracer

    # Include API routers
    app.include_router(api_router, prefix="/api/v1")

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy testing this don't worry",
            "version": settings.app_version,
            "environment": settings.environment
        }

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "Welcome to Research Copilot API",
            "version": settings.app_version,
            "docs": "/docs"
        }

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception",
            error=str(exc),
            url=str(request.url),
            method=request.method,
            exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(exc)}"}
        )

    return app


# Create FastAPI application
app = create_application()

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.environment == "development" else ["yourdomain.com"]
)

# Rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Custom middlewares
setup_middlewares(app)

# Request logging and metrics middleware
@app.middleware("http")
async def add_request_logging_and_metrics(request: Request, call_next):
    start_time = time.time()

    # Set tracing context from request
    import uuid
    tracing_info = extract_tracing_from_request(request)

    # Generate correlation ID if not provided
    correlation_id = tracing_info.get('correlation_id') or str(uuid.uuid4())
    trace_id = tracing_info.get('trace_id') or correlation_id  # Use correlation_id as trace_id if not provided
    span_id = tracing_info.get('span_id') or str(uuid.uuid4())[:16]

    set_tracing_context(
        correlation_id=correlation_id,
        trace_id=trace_id,
        span_id=span_id
    )

    # Get user and organization info from request state
    user = getattr(request.state, 'user', None)
    organization = getattr(request.state, 'organization_obj', None) or getattr(request.state, 'organization_id', None)
    api_key = getattr(request.state, 'api_key', None)

    # Determine user type
    if user and hasattr(user, 'is_superuser') and user.is_superuser:
        user_type = "superuser"
    elif user:
        user_type = "authenticated"
    elif api_key:
        user_type = "api_key"
    else:
        user_type = "anonymous"

    # Determine organization
    org_name = "unknown"
    if organization:
        if hasattr(organization, 'name'):
            org_name = organization.name
        elif isinstance(organization, str):
            org_name = organization

    # Log request
    logger.info(
        "HTTP request started",
        method=request.method,
        url=str(request.url),
        user_type=user_type,
        organization=org_name,
        client_ip=request.client.host if request.client else None
    )

    try:
        response = await call_next(request)

        # Record metrics using performance monitor
        performance_monitor.record_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration=time.time() - start_time,
            user_type=user_type,
            organization=org_name
        )

        # Update system metrics periodically
        if int(time.time()) % 60 == 0:  # Every minute
            performance_monitor.update_system_metrics()

        # Log response
        logger.info(
            "HTTP request completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            duration=time.time() - start_time
        )

        return response

    except Exception as e:
        # Record error metrics
        performance_monitor.record_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=500,
            duration=time.time() - start_time,
            user_type=user_type,
            organization=org_name
        )

        logger.error(
            "HTTP request failed",
            method=request.method,
            url=str(request.url),
            error=str(e),
            duration=time.time() - start_time
        )
        raise

# Include API routers
app.include_router(api_router, prefix="/api/v1")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy testing this don't worry",
        "version": settings.app_version,
        "environment": settings.environment
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Research Copilot API",
        "version": settings.app_version,
        "docs": "/docs"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        error=str(exc),
        url=str(request.url),
        method=request.method,
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )