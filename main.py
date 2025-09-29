from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.endpoints import router as api_router
from core.logging import configure_logging
from core.limiter import limiter
from core.security import SecurityHeadersMiddleware
from core.cache import init_cache, close_cache
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette_prometheus import metrics, PrometheusMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import structlog
import uuid
from domain.models import RequestContext
from core.context import set_request_context

# Configure logging before creating the app instance
configure_logging()

app = FastAPI()

# --- Middleware Configuration ---

# CORS Middleware
# This should be one of the first middleware to be added
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Create a new request context and set it for the current request."""
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    context = RequestContext(correlation_id=correlation_id)
    set_request_context(context)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# Instrument FastAPI for OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# Add Prometheus middleware
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", metrics)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add the rate limiter to the application state and middleware
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Custom exception handler for rate limit exceeded
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )

@app.exception_handler(FileNotFoundError)
async def file_not_found_exception_handler(request: Request, exc: FileNotFoundError):
    logger.error("Configuration file not found.", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "A critical configuration file was not found. Please contact the administrator."},
    )



logger = structlog.get_logger(__name__)


@app.on_event("startup")
async def startup_event():
    logger.info("Application startup")
    init_cache()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown")
    await close_cache()



@app.get("/health", tags=["Monitoring"])
@limiter.limit("10/minute")
async def health_check(request: Request):
    """Health check endpoint to verify service is running."""
    logger.info("Health check endpoint was called")
    return {"status": "ok"}


# Include the API router
app.include_router(api_router, prefix="/api")