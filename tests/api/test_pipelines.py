from http import client
from pathlib import Path
import time

def test_run_asynchronous_dag_pipeline():
    """
    Tests the end-to-end asynchronous pipeline execution, including polling for
    the final document-centric result.
    """
    # Use a small dummy PDF for testing to ensure the test runs quickly.
    pdf_path = Path(__file__).parent.parent / ".." / "dummy.pdf"

    with open(pdf_path, "rb") as pdf_file:
        response = client.post(
            "/api/v1/processing/run",
            files={"file": ("dummy.pdf", pdf_file, "application/pdf")},
            data={"pipeline_name": "advanced_pdf_analysis_dag"},
        )

    assert response.status_code == 200
    job_creation_response = response.json()
    assert "job_id" in job_creation_response
    job_id = job_creation_response["job_id"]

    # Poll the status endpoint until the job is complete
    timeout = 60  # seconds
    start_time = time.time()
    while time.time() - start_time < timeout:
        status_response = client.get(f"/api/v1/processing/status/{job_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()

        if status_data["status"] == "completed":
            # --- Result Validation ---
            assert "result" in status_data
            final_result = status_data["result"]

            # 1. Validate the top-level structure
            assert "results" in final_result
            assert isinstance(final_result["results"], dict)

            # 2. Validate the document-centric structure
            doc_results = final_result["results"]
            assert "document_id" in doc_results
            assert "pages" in doc_results
            assert isinstance(doc_results["pages"], list)

            # 3. Validate a page object
            if doc_results["pages"]:
                page = doc_results["pages"][0]
                assert "page_number" in page
                assert "image_id" in page
                # Check for the aggregated results from the parallel steps
                assert "ocr_result" in page
                assert "vlm_result" in page

            return  # Exit the test successfully

        elif status_data["status"] == "failed":
            assert False, f"Job failed with error: {status_data.get('error')}"

        time.sleep(2)  # Wait before polling again

    assert False, "Job did not complete within the timeout period."