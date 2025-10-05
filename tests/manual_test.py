
import base64
import requests
from pathlib import Path

try:
    # Get the absolute path to the test image
    image_path = Path(__file__).parent / "test_data" / "test_receipt.png"

    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

    data = {
        "pipeline_name": "advanced_pdf_analysis_dag",
        "file": encoded_string,
    }

    response = requests.post("http://localhost:8000/api/v1/processing/run", json=data)

    print(response.status_code)
    print(response.text)
except Exception as e:
    print(f"An error occurred: {e}")