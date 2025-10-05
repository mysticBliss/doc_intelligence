from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, MagicMock
import pytest
from app.core.dependencies import get_storage_service
from tests.mocks.mock_storage_service import MockStorageService
from app.domain.ports.dip_client_port import DIPClientPort
from tests.mocks.mock_dip_client import MockDIPClient


@pytest.fixture
def client():
    app.dependency_overrides[get_storage_service] = lambda: MockStorageService()
    with TestClient(app, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides = {}


@pytest.fixture
def mock_process_document():
    with patch("app.services.document_orchestration_service.DocumentOrchestrationService.process_document") as mock_process:
        mock_process.return_value = {"results": [], "correlation_id": "test-id", "error": None}
        yield mock_process


def test_run_pipeline(client, mock_process_document):
    response = client.post(
        "/api/v1/processing/run",
        files={"file": ("test.pdf", b"fake pdf data", "application/pdf")},
        data={"pipeline_name": "pdf_ocr"},
    )
    assert response.status_code == 200
    assert response.json() == {"results": [], "correlation_id": "test-id", "error": None}


def test_generate(client):
    with patch("app.core.dependencies.get_dip_client") as mock_get_dip_client:
        mock_dip_client = MagicMock(spec=DIPClientPort)
        mock_dip_client.generate.return_value = "Generated text"
        mock_get_dip_client.return_value = mock_dip_client

        response = client.post(
            "/api/v1/processing/generate",
            json={"text": "test text", "image": "test_image"},
            headers={"X-Correlation-ID": "test-id"},
        )
        assert response.status_code == 200
        assert response.json() == {"text": "Generated text", "correlation_id": "test-id"}


def test_generate_without_correlation_id(client):
    with patch("app.api.v1.endpoints.pipelines.get_dip_client") as mock_get_dip_client:
        mock_dip_client = MagicMock(spec=DIPClientPort)
        mock_dip_client.generate.return_value = "Generated text"
        mock_get_dip_client.return_value = mock_dip_client

        response = client.post(
            "/api/v1/processing/generate",
            json={"text": "test text", "image": "test_image"},
        )
        assert response.status_code == 200
        assert "text" in response.json()
        assert "correlation_id" in response.json()