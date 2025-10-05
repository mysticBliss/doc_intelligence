import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CONFIG_DIR: str = os.getenv("CONFIG_DIR", os.path.join(APP_DIR, "engine_templates"))
    OLLAMA_API_BASE_URL: str = "http://ollama:11434"
    REDIS_URL: str = "redis://redis:6379/0"
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"

settings = Settings()