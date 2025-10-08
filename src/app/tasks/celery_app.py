from celery import Celery
from app.core.config import settings

celery = Celery(
    __name__,
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.tasks.celery_worker']
)