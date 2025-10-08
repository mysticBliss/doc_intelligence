
import json
from pathlib import Path
from typing import Dict, List, Any

from app.core.config import settings
from app.core.logging import LoggerRegistry

logger = LoggerRegistry.get_service_logger("pipeline_config")

class PipelineConfig:
    """
    A centralized service for loading and managing document processing pipelines
    from JSON template files.

    This class implements the Singleton pattern to ensure that pipeline templates
    are loaded only once, providing an efficient and consistent source of
    configuration for the entire application. It decouples the processing engine
    from the specifics of configuration management, aligning with the
    "Configuration as Data" principle.
    """
    _instance = None
    _pipeline_configs: Dict[str, Dict[str, Any]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PipelineConfig, cls).__new__(cls)
            cls._instance._load_pipelines()
        return cls._instance

    def _load_pipelines(self):
        """
        Loads all pipeline definitions from .json files in the template directory.
        """
        config_path = Path(settings.CONFIG_DIR)
        logger.info(f"Loading pipeline configurations from: {config_path}")

        if not config_path.is_dir():
            logger.error(f"CRITICAL: Pipeline configuration directory not found at {config_path}.")
            raise RuntimeError(f"Pipeline configuration directory not found: {config_path}")

        self._pipeline_configs = {}

        for file_path in config_path.glob("*.json"):
            logger.debug(f"Attempting to load pipeline configuration from: {file_path}")
            try:
                with open(file_path, "r") as f:
                    config_data = json.load(f)
                    if self._validate_config(config_data, file_path):
                        self._pipeline_configs[config_data["name"]] = config_data
                        logger.info(f"Successfully loaded pipeline: {config_data['name']}")
                    else:
                        logger.warning(f"Skipping invalid configuration file: {file_path}")

            except json.JSONDecodeError:
                logger.error(f"CRITICAL: Failed to decode JSON from {file_path}.")
            except Exception as e:
                logger.error(f"CRITICAL: An unexpected error occurred while loading {file_path}: {e}")
        
        if not self._pipeline_configs:
            logger.warning("No valid pipeline configurations were loaded.")

    def _validate_config(self, config: Dict[str, Any], file_path: Path) -> bool:
        """Validates the structure of a pipeline configuration."""
        required_keys = ["name", "description", "execution_mode", "pipeline"]
        for key in required_keys:
            if key not in config:
                logger.warning(f"Missing required key '{key}' in {file_path}")
                return False
        
        execution_mode = config.get("execution_mode")
        if execution_mode not in ["simple", "dag"]:
            logger.warning(f"Invalid 'execution_mode' ('{execution_mode}') in {file_path}. Must be 'simple' or 'dag'.")
            return False
            
        return True

    def get_pipeline_config(self, name: str) -> Dict[str, Any] | None:
        """
        Retrieves the full configuration for a named pipeline.

        Args:
            name: The name of the pipeline to retrieve.

        Returns:
            A dictionary representing the pipeline's configuration,
            or None if the pipeline name is not found.
        """
        return self._pipeline_configs.get(name)

    def get_all_pipeline_configs(self) -> List[Dict[str, Any]]:
        """
        Returns a list of all loaded pipeline configurations.

        Returns:
            A list of dictionaries, with each dictionary representing a
            pipeline configuration.
        """
        return list(self._pipeline_configs.values())

    def reload_pipelines(self):
        """
        Forces a reload of all pipeline configurations from the source files.
        """
        logger.info("Reloading pipeline configurations...")
        self._load_pipelines()

# Singleton instance for easy access throughout the application
pipeline_config = PipelineConfig()