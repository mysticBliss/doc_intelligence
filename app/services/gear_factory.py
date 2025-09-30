from typing import Dict, Type, List, Any

from app.services.processing_gears.base import ProcessingGear
from app.services.processing_gears.image_preprocessing_gear import ImagePreprocessingGear

# --- Gear Registry ---
# This registry acts as a service locator for our pluggable gears.
# In a more advanced enterprise system, this could be loaded from a configuration
# file or discovered dynamically using entry points.

GEAR_REGISTRY: Dict[str, Type[ProcessingGear]] = {
    ImagePreprocessingGear.gear_name: ImagePreprocessingGear,
    # --- Future Gears (e.g., OCR, VLM) will be registered here ---
    # "ocr_gear": OCRGear,
    # "vlm_classification_gear": VLMClassificationGear,
}

def create_gears(gear_configs: Dict[str, Dict[str, Any]]) -> List[ProcessingGear]:
    """
    Factory function to create a list of processing gear instances.

    This factory is the cornerstone of our pluggable architecture, allowing for
    the dynamic instantiation of processing components based on runtime configuration.

    Args:
        gear_configs: A dictionary where keys are gear names and values are
                      dictionaries of parameters for that gear's constructor.

    Returns:
        A list of instantiated processing gear objects.

    Raises:
        ValueError: If a requested gear is not found in the registry.
    """
    instances = []
    for name, params in gear_configs.items():
        gear_class = GEAR_REGISTRY.get(name)
        if not gear_class:
            # Robust error handling for enterprise-grade reliability
            raise ValueError(f"Unknown processing gear: '{name}'. Available gears: {list(GEAR_REGISTRY.keys())}")
        instances.append(gear_class(**params))
    return instances