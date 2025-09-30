
import json
from pathlib import Path
from typing import Dict, List, Any

from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)

class PipelineConfig:
    """
    A centralized service for loading and managing image processing pipelines
    from a JSON configuration file.

    This class implements the Singleton pattern to ensure that the pipeline
    templates are loaded only once, providing an efficient and consistent
    source of configuration for the entire application. It decouples the
    processing gears from the specifics of configuration management.
    """
    _instance = None
    _pipelines: Dict[str, List[str]] = {}
    _raw_configs: List[Dict[str, Any]] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PipelineConfig, cls).__new__(cls)
            cls._instance._load_pipelines()
        return cls._instance

    def _load_pipelines(self):
        """
        Loads pipeline definitions from the JSON configuration file.

        This method is called once during the instantiation of the Singleton.
        It locates the `pipeline_templates.json` file, parses it, and
        populates the internal `_pipelines` dictionary for quick lookups.
        """
        config_path = Path(settings.CONFIG_DIR) / "pipeline_templates.json"
        logger.info(f"Loading pipeline configurations from: {config_path}")
        try:
            with open(config_path, "r") as f:
                self._raw_configs = json.load(f)
                self._pipelines = {
                    item["name"]: item["steps"] for item in self._raw_configs
                }
                logger.info(f"Successfully loaded {len(self._pipelines)} pipelines.")
        except FileNotFoundError:
            logger.error(f"CRITICAL: Pipeline configuration file not found at {config_path}.")
            self._pipelines = {}
        except json.JSONDecodeError:
            logger.error(f"CRITICAL: Failed to decode JSON from {config_path}.")
            self._pipelines = {}
        except Exception as e:
            logger.error(f"CRITICAL: An unexpected error occurred while loading pipelines: {e}")
            self._pipelines = {}

    def get_pipeline_steps(self, name: str) -> List[str]:
        """

        Retrieves the processing steps for a named pipeline.

        Args:
            name: The name of the pipeline to retrieve.

        Returns:
            A list of strings, where each string is a step in the pipeline.
            Returns an empty list if the pipeline name is not found.
        """
        return self._pipelines.get(name, [])

    def get_all_pipelines(self) -> List[Dict[str, Any]]:
        """
        Returns the raw, unprocessed list of all pipeline configurations.

        This is useful for administrative or debugging interfaces that need
        to display all available pipelines and their metadata.

        Returns:
            A list of dictionaries, with each dictionary representing a
            pipeline configuration.
        """
        return self._raw_configs

# Singleton instance for easy access throughout the application
pipeline_config = PipelineConfig()