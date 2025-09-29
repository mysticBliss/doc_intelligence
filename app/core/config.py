from pydantic import BaseModel
from typing import List
from pydantic_settings import BaseSettings

class AppConfig(BaseSettings):
    models: List[str] = ["qwen2.5vl:3b", "llava:latest"]
    DIP_BASE_URL: str = "http://ollama:11434"
    DIP_GENERATE_TIMEOUT: float = 1800.0 # 30 minutes
    pipeline_templates_path: str = "config/pipeline_templates.json"


    @property
    def default_model(self) -> str:
        if not self.models:
            raise ValueError("No models configured.")
        return self.models[0]

settings = AppConfig()
config = settings # for backwards compatibility if needed