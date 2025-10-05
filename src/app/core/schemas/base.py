from typing import Any, Dict

from pydantic import BaseModel, Field


class BaseProcessorConfig(BaseModel):
    """Base configuration for any processor."""

    name: str
    params: Dict[str, Any] = Field(default_factory=dict)