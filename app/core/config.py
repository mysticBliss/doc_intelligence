import os
from pydantic import BaseModel
from typing import List
from pydantic_settings import BaseSettings

# Determine the project's root directory, assuming this script is in app/core
# This provides a reliable anchor for all file paths.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class AppConfig(BaseSettings):
    models: List[str] = ["qwen2.5vl:3b", "llava:latest"]
    DIP_BASE_URL: str = "http://ollama:11434"
    DIP_GENERATE_TIMEOUT: float = 1800.0  # 30 minutes

    # Directory for configuration files, ensuring paths are robust
    CONFIG_DIR: str = os.path.join(PROJECT_ROOT, 'config')



    @property
    def default_model(self) -> str:
        if not self.models:
            raise ValueError("No models configured.")
        return self.models[0]

settings = AppConfig()
config = settings # for backwards compatibility if needed