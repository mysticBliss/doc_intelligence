import json
from typing import List
from app.domain.models import PipelineTemplate

class PreprocessingService:
    """A service for managing preprocessing pipelines."""

    def __init__(self, templates_file: str = "config/pipeline_templates.json"):
        self.templates = self._load_templates(templates_file)

    def _load_templates(self, templates_file: str) -> List[PipelineTemplate]:
        """Loads pipeline templates from a JSON file."""
        with open(templates_file, "r") as f:
            templates_data = json.load(f)
        return [PipelineTemplate(**template) for template in templates_data]

    def get_all_templates(self) -> List[PipelineTemplate]:
        """Returns all available pipeline templates."""
        return self.templates