import pytest
from app.core.pipeline_config import PipelineConfig


def test_pipeline_config_is_singleton():
    """Tests that the PipelineConfig class behaves as a Singleton."""
    # Act
    config_instance_1 = PipelineConfig()
    config_instance_2 = PipelineConfig()

    # Assert
    assert config_instance_1 is config_instance_2, "PipelineConfig should be a Singleton"


def test_load_and_get_pipeline():
    """Tests loading pipeline configurations and retrieving a specific pipeline."""
    # Arrange
    config = PipelineConfig()
    expected_steps = ["deskew", "to_grayscale", "enhance_contrast", "binarize_adaptive"]

    # Act
    pipeline_steps = config.get_pipeline_steps("Default OCR")

    # Assert
    assert isinstance(pipeline_steps, list)
    assert len(pipeline_steps) > 0
    assert pipeline_steps == expected_steps, "The pipeline steps should match the definition in the config file"