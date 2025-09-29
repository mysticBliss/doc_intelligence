# Document Intelligence API

This is an enterprise-grade API for document intelligence, built with Python and FastAPI. It provides a secure, scalable, and observable platform for processing and analyzing documents using large language models.

## Enterprise-Grade Features

This application is built with a strong focus on enterprise requirements, incorporating the following features:

### Security & Compliance

*   **Rate Limiting**: Protects the application from being overwhelmed by excessive requests.
*   **Security Headers**: Implements essential security headers to protect against common web vulnerabilities like XSS and clickjacking.

### Monitoring & Observability

*   **Structured Logging**: Generates structured, JSON-formatted logs for effective monitoring and debugging.
*   **Prometheus Monitoring**: Exposes a `/metrics` endpoint for Prometheus, enabling enterprise-grade monitoring of key performance indicators.
*   **Distributed Tracing**: Integrates with OpenTelemetry for end-to-end visibility of requests in a microservices environment.

### Code Quality & Testing

*   **Strict Type Checking**: Enforces strict static type checking with `mypy` to ensure a high degree of type safety.
*   **Comprehensive Testing**: Includes a comprehensive testing framework with `pytest`, with a 95% coverage target.
*   **Code Formatting & Linting**: Uses `Ruff` and `black` for consistent code style and quality.

## Architecture

The application is built using the **Hexagonal Architecture** (also known as Ports and Adapters), which promotes a clear separation of concerns and makes the application more modular, testable, and maintainable.

*   **Domain**: Contains the core business logic and data models.
*   **Application**: Orchestrates the business logic and interacts with the domain.
*   **Infrastructure**: Provides implementations for external concerns like databases, APIs, and other services.

## Getting Started

To run the application locally, you will need to have Docker and Docker Compose installed.

1.  **Build and run the Docker container:**

    ```bash
    docker-compose up --build
    ```

2.  **The API will be available at `http://localhost:8000`**

## API Endpoints

The following API endpoints are available:

### `/api/generate`

This endpoint generates text based on a given prompt using the Ollama model.

*   **Method**: `POST`
*   **Request Body**:

    ```json
    {
        "model": "qwen2.5vl:3b",
        "prompt": "Why is the sky blue?"
    }
    ```

*   **Example Request**:

    ```bash
    curl -X POST http://localhost:8000/api/generate \
    -H "Content-Type: application/json" \
    -d '{
        "model": "qwen2.5vl:3b",
        "prompt": "Why is the sky blue?"
    }'
    ```

*   **Example Response**:

    ```json
    {
        "model": "qwen2.5vl:3b",
        "created_at": "2023-10-27T10:00:00.000Z",
        "response": "The sky appears blue to our eyes because of how the Earth's atmosphere scatters sunlight...",
        "done": true
    }
    ```

### `/api/process_pdf`

This endpoint processes a PDF file, converts its pages to images, and sends them to the Ollama vision model along with a user-provided prompt.

*   **Method**: `POST`
*   **Request Body**: `multipart/form-data`
    *   `file`: The PDF file to process.
    *   `text_prompt`: The prompt to send to the vision model.

*   **Example Request**:

    ```bash
    curl -X POST http://localhost:8000/api/process_pdf \
    -F "file=@/path/to/your/document.pdf" \
    -F "text_prompt=My name is John Doe and I live in New York. Please describe the content of this document."
    ```

*   **Example Response**:

    ```json
    {
        "model": "llava:latest",
        "created_at": "2023-10-27T10:05:00.000Z",
        "message": {
            "role": "assistant",
            "content": "The document appears to be a technical diagram..."
        }
    }
    ```

### Monitoring Endpoints

*   `/health`: Returns a 200 OK response if the service is running.
*   `/metrics`: Exposes Prometheus metrics for monitoring.

## Code Quality and Testing

To run the tests and code quality checks:

*   **Run tests**:

    ```bash
    pytest
    ```

*   **Run mypy for type checking**:

    ```bash
    mypy .
    ```

*   **Run ruff for linting**:

    ```bash
    ruff check .
    ```