import base64
import pytest
from app.domain.models import ImageProcessingRequest
from app.services.image_processing_service import ImageProcessingService

# A simple 1x1 white pixel PNG for testing
WHITE_PIXEL_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/wcAAwAB/epv2AAAAABJRU5ErkJggg=="


@pytest.fixture
def image_service() -> ImageProcessingService:
    """Provides an instance of the ImageProcessingService for testing."""
    return ImageProcessingService()


def test_process_image_with_dynamic_pipeline(image_service: ImageProcessingService):
    """Tests that the service can process an image using a dynamically specified pipeline."""
    # Arrange
    pipeline_name = "Default OCR"
    req = ImageProcessingRequest(
        image_data=WHITE_PIXEL_PNG_B64,
        gears_to_run=["image_preprocessor"],
        pipeline_name=pipeline_name
    )
    expected_steps = ["deskew", "to_grayscale", "enhance_contrast", "binarize_adaptive"]

    # Act
    response = image_service.process_image(req)

    # Assert
    assert response.results is not None
    assert len(response.results) == 1
    
    result = response.results[0]
    assert result.gear_name == "image_preprocessor"
    assert result.status == "success"
    assert result.result_data["preprocessing_steps"] == expected_steps
    assert "processed_image_b64" in result.result_data


def test_process_image_with_dynamic_steps(image_service: ImageProcessingService):
    """Tests that the service uses the dynamic preprocessing_steps when provided."""
    # Arrange
    dynamic_steps = ["to_grayscale", "deskew"]
    req = ImageProcessingRequest(
        image_data=WHITE_PIXEL_PNG_B64,
        gears_to_run=["image_preprocessor"],
        preprocessing_steps=dynamic_steps,
        pipeline_name="This should be ignored"
    )

    # Act
    response = image_service.process_image(req)

    # Assert
    assert response.results is not None
    assert len(response.results) == 1
    result = response.results[0]
    assert result.gear_name == "image_preprocessor"
    assert result.status == "success"
    # Verify that the dynamic steps were used, not the ones from any named pipeline
    assert result.result_data["preprocessing_steps"] == dynamic_steps
    assert "processed_image_b64" in result.result_data


def test_process_image_with_no_steps(image_service: ImageProcessingService):
    """Tests that the service handles requests with no preprocessing_steps gracefully."""
    # Arrange
    req = ImageProcessingRequest(
        image_data=WHITE_PIXEL_PNG_B64,
        gears_to_run=["image_preprocessor"],
        preprocessing_steps=None  # Explicitly None
    )

    # Act
    response = image_service.process_image(req)

    # Assert
    assert response.results is not None
    assert len(response.results) == 1
    result = response.results[0]
    assert result.gear_name == "image_preprocessor"
    assert result.status == "success"
    # Expect an empty list of steps
    assert result.result_data["preprocessing_steps"] == []
    assert "processed_image_b64" in result.result_data