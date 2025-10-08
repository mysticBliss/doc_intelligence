from fastapi import FastAPI
from .api.v1.router import api_router
from .core.logging import LoggerRegistry

# Configure enterprise logging
logger = LoggerRegistry.get_api_logger("main")

app = FastAPI(
    title="Document Intelligence API",
    description="An enterprise-grade API for document processing and intelligence.",
    version="1.0.0",
)

app.include_router(api_router, prefix="/api/v1")

# Log application startup
logger.info("Document Intelligence API initialized", version="1.0.0")