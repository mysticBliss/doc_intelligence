from fastapi import FastAPI
from .api.v1.router import api_router
from .core.logging import get_logger

# Configure logging
logger = get_logger(__name__)

app = FastAPI(
    title="Document Intelligence API",
    description="An enterprise-grade API for document processing and intelligence.",
    version="1.0.0",
)

app.include_router(api_router, prefix="/api/v1")