import pytest
from app.services.template_service import TemplateService
from app.domain.models import PipelineTemplate


def test_template_service_loads_templates():
    """Tests that the TemplateService can successfully load pipeline templates."""
    # Arrange
    service = TemplateService()

    # Act
    templates = service.get_all_templates()

    # Assert
    assert templates is not None
    assert isinstance(templates, list)
    assert len(templates) > 0
    assert all(isinstance(t, PipelineTemplate) for t in templates)