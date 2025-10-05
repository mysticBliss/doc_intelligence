from fastapi import APIRouter, Depends
from app.domain.models import PipelineTemplate
from app.services.preprocessing_service import PreprocessingService
from app.core.dependencies import get_preprocessing_service
from typing import List

router = APIRouter()

@router.get("/pipelines", response_model=List[PipelineTemplate])
async def list_preprocessing_pipelines(service: PreprocessingService = Depends(get_preprocessing_service)):
    """Returns a list of available preprocessing pipeline templates."""
    return service.get_all_templates()

@router.get("/steps", response_model=List[str])
async def list_preprocessing_steps() -> List[str]:
    """Returns a list of available preprocessing steps."""
    return ["deskew", "to_grayscale", "enhance_contrast", "binarize_adaptive", "denoise"]