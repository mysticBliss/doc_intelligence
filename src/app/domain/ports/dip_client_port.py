from abc import ABC, abstractmethod
from typing import Any, Dict

class DIPClientPort(ABC):
    """Port for the Document Intelligence Platform client."""

    @abstractmethod
    def run_pipeline(self, pipeline_name: str, file_path: str) -> Dict[str, Any]:
        """Runs a pipeline on a file."""
        pass