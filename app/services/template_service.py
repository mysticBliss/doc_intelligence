import json
from typing import List
from pydantic import ValidationError
import structlog

from domain.models import PipelineTemplate
from core.config import config

logger = structlog.get_logger(__name__)

class TemplateService:
    """Manages loading and accessing pipeline templates."""

    def __init__(self, template_path: str = config.pipeline_templates_path):
        self._template_path = template_path
        self._templates = self._load_templates()

    def _load_templates(self) -> List[PipelineTemplate]:
        """Loads and validates templates from the JSON file."""
        try:
            with open(self._template_path, "r") as f:
                data = json.load(f)
            
            # Use Pydantic for validation
            templates = [PipelineTemplate(**item) for item in data]
            logger.info(f"Successfully loaded {len(templates)} pipeline templates.")
            return templates
        except FileNotFoundError:
            logger.error("Pipeline templates file not found.", path=self._template_path)
            raise
        except json.JSONDecodeError:
            logger.error("Failed to decode pipeline templates JSON.", path=self._template_path)
            return []
        except ValidationError as e:
            logger.error("Invalid template structure in pipeline templates file.", errors=e.errors())
            return []

    def get_all_templates(self) -> List[PipelineTemplate]:
        """Returns all loaded pipeline templates."""
        return self._templates