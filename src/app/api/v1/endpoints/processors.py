from fastapi import APIRouter
from app.processing.factory import ProcessorFactory

router = APIRouter()

# Instantiate the factory to access the registry
factory = ProcessorFactory()
PROCESSOR_REGISTRY = factory._processor_registry

@router.get("/", summary="List Available Processors")
def list_processors():
    """
    Returns a list of available processor names.
    """
    return list(PROCESSOR_REGISTRY.keys())