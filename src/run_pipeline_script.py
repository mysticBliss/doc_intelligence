import json
import os
import time
from typing import Optional

import requests

# Configuration (can be overridden via environment variables)
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000/api/v1")
PDF_FILE_PATH = os.getenv("PDF_FILE_PATH", "/app/sample-invoice.pdf")
TEMPLATE_NAME = os.getenv("TEMPLATE_NAME", "advanced_pdf_analysis_dag")


def run_pipeline(file_path: str, template_name: str, max_attempts: int = 5, timeout: int = 30) -> Optional[dict]:
    """Send a PDF to the processing API and save/return the JSON response.

    Retries on connection errors and 5xx responses using exponential backoff.
    Returns the parsed JSON response on success, otherwise None.
    """
    print("--- Script execution started ---")
    url = f"{API_BASE_URL.rstrip('/')}/processing/run"

    print(f"Checking for file at: {file_path}")
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return None

    response_json = None
    with open(file_path, "rb") as fh:
        files = {"file": (os.path.basename(file_path), fh, "application/pdf")}
        data = {"pipeline_name": template_name}

        for attempt in range(1, max_attempts + 1):
            try:
                print(f"Attempt {attempt}/{max_attempts}: POST {url} (timeout={timeout}s)")
                response = requests.post(url, files=files, data=data, timeout=timeout)

                print(f"Status Code: {response.status_code}")
                print("--- Response Headers ---")
                for k, v in response.headers.items():
                    print(f"{k}: {v}")

                # Print short body preview for debugging
                body_preview = response.text[:2000]
                print("--- Response Text (preview, truncated) ---")
                print(body_preview)

                # If we got a successful HTTP status, try to parse JSON and exit
                if 200 <= response.status_code < 300:
                    try:
                        response_json = response.json()
                        print("--- Response JSON ---")
                        print(json.dumps(response_json, indent=2))
                        # Try to persist the response for later inspection (best-effort)
                        try:
                            out_path = os.getenv("RESPONSE_SAVE_PATH", "/app/response.json")
                            with open(out_path, "w", encoding="utf-8") as out_f:
                                json.dump(response_json, out_f, indent=2)
                            print(f"Saved full JSON response to {out_path}")
                        except Exception as write_err:
                            print(f"Warning: failed to save response JSON: {write_err}")
                        return response_json
                    except json.JSONDecodeError:
                        print("Warning: Response is not valid JSON. See response text above.")
                        return None

                # Retry on server errors (5xx)
                if 500 <= response.status_code < 600 and attempt < max_attempts:
                    backoff = 2 ** attempt
                    print(f"Server error {response.status_code}. Retrying after {backoff}s...")
                    time.sleep(backoff)
                    continue

                # Do not retry for client errors (4xx) or if max attempts reached
                print("Non-retriable response or max attempts reached. Exiting.")
                return None

            except requests.exceptions.ConnectionError as e:
                print(f"ConnectionError on attempt {attempt}: {e}")
                if attempt < max_attempts:
                    backoff = 2 ** attempt
                    print(f"Retrying after {backoff}s...")
                    time.sleep(backoff)
                    continue
                else:
                    print("Exceeded maximum retries due to connection errors.")
                    return None
            except requests.exceptions.Timeout:
                print(f"Timeout on attempt {attempt} (timeout={timeout}s)")
                if attempt < max_attempts:
                    backoff = 2 ** attempt
                    print(f"Retrying after {backoff}s...")
                    time.sleep(backoff)
                    continue
                else:
                    print("Exceeded maximum retries due to timeouts.")
                    return None
            except requests.exceptions.RequestException as e:
                print(f"RequestException: {e}")
                return None

    print("--- Script execution finished ---")
    return response_json


if __name__ == "__main__":
    print("--- Starting script ---")
    result = run_pipeline(PDF_FILE_PATH, TEMPLATE_NAME)
    if result is not None:
        print("Pipeline run completed successfully.")
    else:
        print("Pipeline run failed or returned no JSON.")
    print("--- Script finished ---")