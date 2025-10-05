
import sys
sys.path.insert(0, 'c:\\Users\\HP\\MyDrive\\Repos\\git_saqie\\doc_intelligence\\src')

import base64
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.dependencies import get_storage_service
from app.main import app
from tests.mocks.mock_storage_service import MockStorageService

app.dependency_overrides[get_storage_service] = lambda: MockStorageService()
client = TestClient(app)

def test_run_pipeline():
    # Get the absolute path to the test image
    image_path = Path(__file__).parent.parent / "test_data" / "test_receipt.png"

    with open(image_path, "rb") as image_file:
        response = client.post(
            "/api/v1/processing/run",
            files={"file": ("test_receipt.png", image_file, "image/png")},
            data={"pipeline_name": "ocr_pipeline"},
        )
    assert response.status_code == 200
    response_json = response.json()
    assert "results" in response_json
    assert len(response_json["results"]) == 1
    assert response_json["results"][0]["processor_name"] == "ocr_processor"
    assert response_json["results"][0]["status"] == "success"