from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    """
    Checks the health of the application.
    """
    return {"status": "ok"}