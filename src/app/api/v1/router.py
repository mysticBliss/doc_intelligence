from fastapi import APIRouter
from app.api.v1.endpoints import (health, pipeline_templates, pipelines,
                                  processors, ws)

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(pipelines.router, prefix="/processing", tags=["processing"])
api_router.include_router(pipeline_templates.router, prefix="/pipeline-templates", tags=["pipeline-templates"])
api_router.include_router(processors.router, prefix="/processors", tags=["processors"])
api_router.include_router(ws.router, prefix="/ws", tags=["websockets"])