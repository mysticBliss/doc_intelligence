
> **Note:** This document contains important architectural guidelines and technical workflows. Please read it carefully before contributing to the project.

## Core Evaluation Framework
For every feature/component, analyze through:

**Enterprise Pillars**
- Security & Compliance (data classification, encryption, audit trails, regulatory requirements)
- Data Governance (metadata, lineage, quality, retention, master data management)
- Integration Architecture (APIs, event-driven patterns, enterprise service bus, legacy compatibility)
- Scalability & Performance (horizontal scaling, load balancing, capacity planning, multi-tenancy)
- Operational Excellence (monitoring, DevOps integration, maintainability, documentation)

**Python Enterprise Patterns (Mandatory)**
- **Hexagonal Architecture**: Ports & adapters for external dependencies isolation
- **Domain-Driven Design**: Bounded contexts, aggregate roots, repository pattern
- **CQRS**: Separate read/write models with command/query handlers
- **Factory & Strategy**: Plugin architecture with Protocol classes for extensibility
- **Dependency Injection**: Configuration-driven component wiring
- **Decorator Pattern**: Cross-cutting concerns (audit, security, monitoring)
- **Circuit Breaker & Saga**: Resilience and distributed transaction handling

**Code Quality Standards**
- Type hints with mypy strict mode, Pydantic validation
- Structured logging with correlation IDs for distributed tracing
- FastAPI/SQLAlchemy for type-safe APIs and data access
- Comprehensive testing (unit, integration, contract, property-based)
- Black/Ruff formatting, Bandit security scanning

## Response Structure
Always provide:
1. **Enterprise Risk Assessment** - Scale and integration risks
2. **Pattern Compliance** - Required Python patterns and architecture decisions
3. **Quality Gates** - Type safety, testing, security requirements  
4. **Integration Strategy** - Enterprise ecosystem fit and API design
5. **Implementation Roadmap** - Phased approach with architectural milestones

## Key Challenge Questions
- How does this scale to enterprise volumes with proper resource management?
- Which Python patterns ensure modularity and testability?
- What are the data governance and compliance implications?
- How does this integrate with existing enterprise Python toolchain?
- What happens during failure scenarios and how do we recover?
- Can this be deployed, monitored, and maintained by enterprise ops teams?

## Decision Criteria
Prioritize: Enterprise integration > Long-term maintainability > Developer productivity > Feature completeness

## Project Working and testing
REMEMBER I AM USING DOCKER COMPOSE THAT HOSTED MY PLATFORM. suggest changes based on that since i cant run commands
All commands, especially for testing and validation, must be executed within the context of the appropriate service container.

## Enterprise Logging Standards

**NEVER introduce any new logging libraries. Use only the existing `structlog` logger with the enterprise LoggerRegistry pattern.**

### Enterprise Logging Architecture

The application implements a **centralized logging configuration** with **hierarchical logger instances** following enterprise best practices. All logging uses `structlog` to produce structured JSON logs for effective monitoring, debugging, and analysis.

#### **LoggerRegistry Pattern (Mandatory)**

All loggers MUST be created using the `LoggerRegistry` class to ensure consistent naming and configuration:

```python
from app.core.logging import LoggerRegistry

# API Layer Loggers
api_logger = LoggerRegistry.get_api_logger("endpoints")
main_logger = LoggerRegistry.get_api_logger("main")

# Service Layer Loggers
orchestration_logger = LoggerRegistry.get_service_logger("orchestration")
config_logger = LoggerRegistry.get_service_logger("pipeline_config")

# Processing Layer Loggers
pipeline_logger = LoggerRegistry.get_pipeline_logger()
processor_logger = LoggerRegistry.get_processor_logger("ocr_processor")

# Infrastructure Layer Loggers
celery_logger = LoggerRegistry.get_infrastructure_logger("celery")
dip_logger = LoggerRegistry.get_infrastructure_logger("dip_client")

# Security & Audit Loggers
security_logger = LoggerRegistry.get_security_logger()
```

#### **Hierarchical Logger Naming Convention**

All loggers follow a strict hierarchical naming pattern:

- **API Layer**: `api.{component}` (e.g., `api.main`, `api.endpoints`)
- **Service Layer**: `service.{service_name}` (e.g., `service.orchestration`)
- **Processing Layer**: `processor.{processor_name}` (e.g., `processor.ocr_processor`)
- **Pipeline Layer**: `pipeline.execution`
- **Infrastructure Layer**: `infrastructure.{component}` (e.g., `infrastructure.celery`)
- **Security Layer**: `security.audit`

#### **Enterprise Logging Structure**

Each log entry follows a structured JSON format universally supported by enterprise log management platforms:

```json
{
    "timestamp": "2025-10-07T16:13:24.547342Z",
    "level": "info",
    "event": "Pipeline execution completed successfully",
    "logger": "infrastructure.celery",
    "correlation_id": "7132e41c-f960-468c-be31-2755751649e0",
    "job_id": "7132e41c-f960-468c-be31-2755751649e0",
    "pipeline_name": "advanced_pdf_analysis_dag",
    "document_id": "869efa9570c239ed4cd4a53c03cbc00f",
    "status": "success"
}
```

#### **Mandatory Logging Rules**

1. **DO** use keyword arguments for all contextual data:
   ```python
   logger.info(
       "Pipeline execution completed successfully",
       job_id=result.job_id,
       status=result.status.value,
       correlation_id=correlation_id
   )
   ```

2. **DO NOT** use f-strings, `.format()`, or string concatenation in log messages:
   ```python
   # FORBIDDEN - breaks structured format
   logger.info(f"Pipeline {pipeline_name} completed with status {status}")
   ```

3. **DO** include correlation IDs for distributed tracing:
   ```python
   logger = logger.bind(correlation_id=correlation_id)
   ```

4. **DO** use consistent event naming patterns:
   - `{component}.{action}.{status}` (e.g., `"pipeline.execution.started"`)
   - `{processor}.{operation}.{outcome}` (e.g., `"ocr.processing.finished"`)

#### **Logger Creation Guidelines**

**✅ CORRECT - Use LoggerRegistry:**
```python
from app.core.logging import LoggerRegistry

class DocumentOrchestrationService:
    def __init__(self, logger=None):
        self.logger = logger or LoggerRegistry.get_service_logger("orchestration")
```

**❌ FORBIDDEN - Direct structlog calls:**
```python
# DO NOT USE - bypasses enterprise standards
import structlog
logger = structlog.get_logger(__name__)
```

#### **Enterprise Benefits Achieved**

1. **Component Identification**: Easy filtering by service, processor, or infrastructure
2. **Operational Excellence**: Enhanced monitoring and debugging capabilities
3. **Centralized Configuration**: Single point of logging configuration
4. **Hierarchical Organization**: Consistent naming across all components
5. **Structured Output**: Machine-parseable JSON for automated analysis
6. **Distributed Tracing**: Correlation IDs for request tracking across services

This enterprise logging architecture ensures **observability**, **traceability**, and **maintainability** required for production-grade applications while following industry best practices.

#### **Implementation Status**

The following components have been updated to use the new `LoggerRegistry` pattern:

**✅ Completed:**
- `src/app/main.py` - Uses `LoggerRegistry.get_api_logger("main")`
- `src/app/services/document_orchestration_service.py` - Uses `LoggerRegistry.get_service_logger("orchestration")`
- `src/app/processing/factory.py` - Uses `LoggerRegistry.get_processor_logger(processor_name)`
- `src/app/processing/pipeline.py` - Uses `LoggerRegistry.get_pipeline_logger()`
- `src/app/processing/decorators.py` - Uses `LoggerRegistry.get_decorator_logger()`
- `src/app/tasks/celery_worker.py` - Uses `LoggerRegistry.get_infrastructure_logger("celery")`
- `src/app/infrastructure/dip_client.py` - Uses `LoggerRegistry.get_infrastructure_logger("dip_client")`
- `src/app/core/pipeline_config.py` - Uses `LoggerRegistry.get_service_logger("pipeline_config")`

**📋 Future Enhancements:**
- API endpoints should use `LoggerRegistry.get_api_logger("endpoints")`
- Individual processors should use `LoggerRegistry.get_processor_logger(processor_name)`
- Security events should use `LoggerRegistry.get_security_logger()`

#### **Logger Count Optimization**

**Before**: 15-20+ inconsistent logger instances with mixed naming patterns
**After**: 6 standardized logger categories with hierarchical naming:

1. **API Loggers** (1-2 instances): `api.main`, `api.endpoints`
2. **Service Loggers** (2-3 instances): `service.orchestration`, `service.pipeline_config`
3. **Processor Loggers** (7+ instances): `processor.{processor_name}` (one per processor type)
4. **Pipeline Logger** (1 instance): `pipeline.execution`
5. **Infrastructure Loggers** (2-3 instances): `infrastructure.celery`, `infrastructure.dip_client`
6. **Security Logger** (1 instance): `security.audit`

## PDF and Images Processing Architecture

### **Document-Image Relationship Model**

The platform implements a hierarchical document-image relationship model:

**Parent-Child Relationship:**
- **PDF Document**: Has unique `document_id` (MD5 hash of file content)
- **Extracted Images**: Each page becomes a separate image with unique `image_id`
- **Relationship**: `parent_document_id` links images back to source PDF
- **Page Context**: `page_number` maintains page order and context

**Data Flow:**
```
PDF File → document_id (parent) → Page Images → image_id (children)
         └─ parent_document_id ←─────────────────┘
```

**Special Cases:**
- **Single Image Upload**: No parent-child relationship needed
- **Single Page PDF**: Parent-child relationship maintained for consistency
- **Multi-page PDF**: Full hierarchical structure with page numbering

### **Image Processing Pipeline**

**PDF Extraction Process:**
1. **Input**: PDF file with `document_id`
2. **Processing**: `pdf_extraction_processor` converts each page to image
3. **Output**: Array of `DocumentPayload` objects (one per page)
4. **Format**: PNG/JPEG at configurable DPI (default: 300)

**Image Enhancement Pipeline:**
- **Preprocessing**: Deskew, denoise, binarize, perspective correction
- **OCR Optimization**: Page segmentation, language detection
- **VLM Preparation**: Format optimization for vision models

**Metadata Preservation:**
```json
{
  "document_id": "869efa9570c239ed4cd4a53c03cbc00f",
  "parent_document_id": "d1b78acc-83b6-485b-bb62-253d46a2adfe",
  "page_number": 2,
  "image_format": "PNG",
  "resolution": 300,
  "image_dimensions": [2480, 3508]
}
```

## API Endpoints
- All API endpoints must be fully functional and thoroughly tested.
- The API implementation should be **enterprise-grade**, addressing the following key areas:
  - Security (authentication, authorization, encryption)
  - Scalability and performance
  - Reliability and fault tolerance
  - Compliance with relevant standards and regulations
  - Clear documentation for each endpoint
- The `/api/v1/processing/run` endpoint is the single, generic entry point for all document processing workflows. All pipeline logic is defined in JSON templates stored in `src/app/engine_templates/`. The `/run` endpoint dynamically loads and executes the pipeline defined in the specified JSON template.
- The API must support robust integration and extensibility for future requirements.

## Docker working commands
docker compose up -d --build
docker compose build
docker compose up -d
docker compose down
docker compose exec <service_name> <command>
docker compose logs <service_name>
docker compose ps
docker compose restart <service_name>
docker compose stop <service_name>
docker compose start <service_name>
docker compose rm <service_name>
docker compose pull
docker compose logs api
never run `docker compose logs -f api` instead run `docker compose logs api`

## Must check before merging to main branch:
You dont delete any existing functionality
You retain the working on the testing and make sure it works as expected
You validate with a DRY analysis that the code is not breaking any existing functionality


## Before you change or add any new functionality, please make sure to:
1. Review the existing codebase to ensure that the new feature does not break any existing functionality.
       tree <project-directory>
2. Validate the new feature with a DRY analysis to confirm that it does not introduce any regressions.
3. Test the new feature thoroughly to ensure that it meets the required quality standards.
There are 2 requirements file
1) api.requirements.txt
2) ui.requirements.txt

## Advanced Preprocessing Enhancements
The `ImagePreprocessingProcessor` has been significantly enhanced to support a configurable pipeline of advanced image manipulation steps. This allows for fine-tuned optimization of images before they are sent for OCR or VLM analysis, dramatically improving the accuracy of data extraction.

Each step is defined as an object in the `steps` array, specifying the `name` of the operation and its `params`.

### Available Steps and Parameters

- **`deskew`**: Automatically straightens a skewed image.
- **`denoise`**: Reduces noise using non-local means denoising.
  - `h`: (Optional) Luminance component filter strength.
  - `templateWindowSize`: (Optional) Template patch size for averaging.
  - `searchWindowSize`: (Optional) Search window size for patches.
- **`binarize`**: Converts an image to black and white.
  - `method`: (Optional) `adaptive` or `otsu`.
  - `adaptiveMethod`: (Optional, if method is `adaptive`) `mean` or `gaussian`.
  - `blockSize`: (Optional, if method is `adaptive`) Size of the pixel neighborhood.
  - `C`: (Optional, if method is `adaptive`) Constant subtracted from the mean.
- **`opening`**: Removes small noise (erosion followed by dilation).
  - `kernel_size`: (Optional) The size of the morphological kernel.
- **`closing`**: Closes small holes in objects (dilation followed by erosion).
  - `kernel_size`: (Optional) The size of the morphological kernel.
- **`canny`**: Detects edges in the image.
  - `threshold1`: (Optional) First threshold for the hysteresis procedure.
  - `threshold2`: (Optional) Second threshold for the hysteresis procedure.
- **`correct_perspective`**: Warps the image to correct perspective distortion.

### Example `image_preprocessing.json` Template
This template demonstrates a comprehensive preprocessing pipeline:
```json
{
  "name": "image_preprocessing",
  "description": "Applies a full suite of advanced preprocessing steps to an image.",
  "execution_mode": "simple",
  "pipeline": [
    {
      "name": "image_preprocessing_processor",
      "params": {
        "steps": [
          {
            "name": "correct_perspective"
          },
          {
            "name": "opening",
            "params": {
              "kernel_size": 3
            }
          },
          {
            "name": "closing",
            "params": {
              "kernel_size": 3
            }
          }
        ]
      }
    }
  ]
}
```

## Verified Parameter Types for Processors
To enhance robustness and type safety, all processors now use Pydantic models to validate their configuration parameters. This ensures that pipelines fail fast with clear error messages if a parameter is missing or has an incorrect type.

### `OcrProcessor`
- **`language`**: Specifies the language for the Tesseract OCR engine.
  - **Type**: `str`
  - **Default**: `"eng"`
  - **Example**:
    ```json
    {
      "name": "ocr_processor",
      "params": {
        "language": "deu"
      }
    }
    ```

### `VlmProcessor`
- **`prompt`**: The text prompt to guide the Vision Language Model's analysis.
  - **Type**: `str`
  - **Required**: Yes
- **`model`**: The specific OLLAMA model to use.
  - **Type**: `str`
  - **Default**: `"llava"`
- **`temperature`**: Controls the randomness of the model's output.
  - **Type**: `float`
  - **Default**: `0.5`
  - **Example**:
    ```json
    {
      "name": "vlm_processor",
      "params": {
        "prompt": "What is the total amount on this receipt?",
        "model": "bakllava",
        "temperature": 0.2
      }
    }
    ```

### `PDFImageExtractionProcessor`
- **`dpi`**: Dots Per Inch for rendering PDF pages as images. Higher values produce larger, more detailed images.
  - **Type**: `int`
  - **Default**: `300`
- **`image_format`**: The output format for the extracted images.
  - **Type**: `str` (Enum: `"jpeg"`, `"png"`)
  - **Default**: `"jpeg"`
  - **Example**:
    ```json
    {
      "name": "pdf_extraction_processor",
      "params": {
        "dpi": 600,
        "image_format": "png"
      }
    }
    ```

## APP Logic 2
similarly capablities are a list of Processors like OCR, PDFProcessor, ImageProcessors, we should be able to list them and be able to create a pipeline based a combination of Processors (asynchronouly or synchrnously)​

## App Logic 3
## Current Implementation

The document intelligence platform is built on a modular, extensible, and enterprise-grade processing engine. This engine is designed to handle complex document processing workflows in a scalable, maintainable, and secure manner. The key components of this architecture are the `ProcessingPipeline`, the `ProcessorFactory`, and a standardized set of `BaseProcessor` implementations.

The core of the application is the `ProcessingPipeline`, an engine designed around a dynamic, **"Configuration as Data"** architecture. This principle separates the *what* (the business process defined in a JSON object) from the *how* (the stable, underlying execution logic).

The engine supports two modes of execution:

1.  **Synchronous Execution:** For immediate processing, the API returns the results directly to the client.
2.  **Asynchronous Execution:** For long-running tasks, the API returns a `job_id` that can be used to track the status of the job. The processing is handled in the background by a Celery worker.

This dual-mode execution model provides the flexibility to handle a wide range of use cases, from real-time analysis to batch processing of large documents. 

## APP Logic 5
The ollama service is indeed hosted separately, and the api service should communicate with it via HTTP requests, not by importing the ollama library directly. My previous change was incorrect.

## Command Logic
Before you finish the task, please review the code and ensure it meets the following criteria:
1. All API endpoints must be fully functional and thoroughly tested.
2. The API implementation should be enterprise-grade, addressing security, scalability, reliability, compliance, and documentation.
3. Ensure that the code adheres to the established coding standards, including type hints, structured logging, and comprehensive testing.
4. Validate that the implementation aligns with the Hexagonal Architecture and Domain-Driven Design principles.
5. Confirm that the implementation does not introduce any new logging libraries and uses the existing structlog logger.
6. Ensure that the implementation supports robust integration and extensibility for future requirements.
7. Verify that the implementation includes proper error handling and logging for observability.
8. Make sure to test the implementation within the context of the appropriate service container using Docker Compose commands.
9. Conduct a DRY analysis to ensure that the code does not break any existing functionality.
10. Review the implementation for compliance with data governance and regulatory requirements.
11. Ensure that the implementation includes a unique ID for PDFs and establishes a father-son relationship with images when applicable.
12. Provide a detailed implementation roadmap with phased approaches and architectural milestones.
13. Finally, document any changes made and update relevant documentation to reflect the new implementation.

## Core Engine Architecture

The document intelligence platform is built on a modular, extensible, and enterprise-grade processing engine. This engine is designed to handle complex document processing workflows in a scalable, maintainable, and secure manner. The key components of this architecture are the `ProcessingPipeline`, the `ProcessorFactory`, and a standardized set of `BaseProcessor` implementations.

### ProcessingPipeline

The `ProcessingPipeline` is the orchestrator of the entire processing workflow. It takes a pipeline configuration and a `ProcessorFactory` and executes the defined steps. Its primary responsibility is to manage the data flow between processors, ensuring that the output of one step is correctly formatted and passed as the input to the next.

**Data Flow Management:**

In a linear pipeline, the `ProcessingPipeline` iterates through the configured processors. After each processor executes, the pipeline takes the `ProcessorResult`, extracts the relevant output (e.g., image data from the `pdf_extraction_processor`), and creates a *new* `DocumentPayload` for the next processor in the sequence. This ensures that processors are decoupled and that each one receives the data in the expected format.

### ProcessorFactory

The `ProcessorFactory` is a singleton class that is responsible for creating and managing all processor instances. It maintains a registry of all available processors and provides a single point of access for creating new processor instances. This ensures that all processors are created in a consistent and controlled manner.

The `ProcessorFactory` is implemented as a singleton to ensure that there is only one instance of the factory in the application. This is important because the factory maintains a registry of all available processors, and we want to avoid having multiple registries in the application.

The `ProcessorFactory` is also responsible for injecting any dependencies that a processor may have. For example, the `EnhancedPdfProcessor` requires an instance of the `ProcessorFactory` to create its sub-processors. The `ProcessorFactory` injects this dependency when it creates the `EnhancedPdfProcessor` instance.

### Processor Architecture

At the heart of the engine is the `BaseProcessor`, an abstract base class that defines a standardized interface for all processing components. This ensures that every processor, regardless of its specific function, adheres to a common contract.

**`BaseProcessor` Contract:**

-   **Initialization**: Each processor is initialized with a `name`, a `config` dictionary, and a `logger` instance. The `config` allows for flexible, instance-specific parameterization.
-   **`process()` Method**: The core of the processor, this method accepts a `DocumentPayload` and returns a `ProcessorResult`. This standardized signature ensures that processors can be chained together seamlessly.
-   **`validate_config()` Method**: Each processor is responsible for validating its own configuration, ensuring that it has all the necessary parameters to execute correctly.
-   **`instrument_step` Decorator**: This decorator automatically captures metadata about each processing step, including execution time, status (success or failure), and any error messages. This is critical for observability and debugging.

### Instrumentation Decorators

The engine provides two key decorators, `@instrument_step` and `@instrument_sub_step`, to standardize logging, timing, and error handling across all processors. This approach aligns with our **Decorator Pattern** for cross-cutting concerns, promoting DRY principles and ensuring consistent observability.

-   **`@instrument_step`**:
    -   **Purpose**: Applied to the main `process` method of any `BaseProcessor` subclass.
    -   **Functionality**: It wraps the core processing logic to automatically handle:
        -   **Timing**: Captures the start and end time of the processor's execution.
        -   **Logging**: Logs the start, success, or failure of the step with structured metadata.
        -   **Error Handling**: Catches any exceptions, logs the error, and returns a standardized `ProcessorResult` with a `FAILURE` status.
        -   **Metadata**: Enriches logs with context such as `processor_name`, `job_id`, and `request_id`.
    -   **Usage**:
        ```python
        from app.processing.decorators import instrument_step

        class MyProcessor(BaseProcessor):
            @instrument_step
            async def process(self, payload: DocumentPayload) -> ProcessorResult:
                # Core logic here
        ```

-   **`@instrument_sub_step`**:
    -   **Purpose**: Used for instrumenting discrete, internal functions within a processor, such as the individual operations in `ImagePreprocessingProcessor` (e.g., `deskew`, `denoise`).
    -   **Functionality**: Similar to `@instrument_step`, but designed for finer-grained monitoring. It captures:
        -   Execution time of the sub-step.
        -   Input and output image hashes to track data transformation.
        -   Parameters used in the sub-step.
    -   **Usage**:
        ```python
        from app.processing.decorators import instrument_sub_step

        class ImagePreprocessingProcessor(BaseProcessor):
            @instrument_sub_step
            def deskew(self, image: np.ndarray) -> np.ndarray:
                # Deskewing logic here
        ```

By mandating the use of these decorators, we enforce a consistent, enterprise-grade approach to instrumentation, making the system more transparent, maintainable, and easier to debug.

**`DocumentPayload` and `ProcessorResult` Data Contracts:**

To ensure type safety and a consistent data flow between processors, the engine uses two key Pydantic models:

-   `DocumentPayload`: This model encapsulates the data that is passed *into* a processor. It includes the `image_data` (as bytes) and a `metadata` dictionary.
-   `ProcessorResult`: This model encapsulates the data that is returned *from* a processor. It includes the `status`, the `processor_name`, and the `results` of the operation.

### Available Processors

The platform includes a suite of built-in processors, each designed to perform a specific task:

-   **`ImagePreprocessingProcessor`**: Improves image quality through a pipeline of steps like deskewing, denoising, and contrast enhancement.
-   **`OcrProcessor`**: Extracts text from images using Tesseract OCR.
-   **`PDFImageExtractionProcessor``**: Converts PDF pages into images for further processing.
-   **`VlmProcessor`**: Integrates with a Vision Language Model (VLM) via OLLAMA for advanced image analysis.
-   **`EnhancedPdfProcessor`**: An orchestrator processor that manages a complex workflow of other processors to handle end-to-end PDF processing.

### Advanced `ProcessingPipeline` Data Flow Logic
The `_run_linear` method in `ProcessingPipeline` now supports a more sophisticated data flow. It correctly handles the output of a processor and passes it as the input to the next. It can process different types of results from processors, including:

- A list of `DocumentPayload` objects.
- A dictionary containing an 'images' key with a list of `DocumentPayload` objects.
- Other dictionary types that are passed as metadata.

This ensures that processors can be chained together in complex pipelines, and the documentation should specify how to format processor results to be compliant with this new logic.

### Asynchronous Task Execution with Celery

#### **Celery Worker Implementation Standards**

The `run_pipeline_task` in `celery_worker.py` follows enterprise patterns for reliable task execution:

**✅ CORRECT Implementation Pattern:**
```python
@celery.task(bind=True)
def run_pipeline_task(self, pipeline_config, file_data, file_name, correlation_id):
    logger = LoggerRegistry.get_infrastructure_logger("celery")

    # Initialize result outside try block for proper scope
    result = None

    try:
        result = loop.run_until_complete(main())

        # Update Celery's state with final result
        self.update_state(
            state='SUCCESS',
            meta={'result': result.model_dump_json()}
        )

        logger.info(
            "Pipeline execution completed successfully",
            job_id=result.job_id,
            status=result.status.value,
            correlation_id=correlation_id
        )

        # Return JSON string for consistent format
        return result.model_dump_json()

    except Exception:
        logger.exception("Celery task failed unexpectedly", correlation_id=correlation_id)
        self.update_state(
            state='FAILURE',
            meta={'error': 'Pipeline execution failed'}
        )
        raise
    finally:
        loop.close()
```

**Key Requirements:**
1. **Variable Scope**: Initialize `result = None` before try block
2. **State Management**: Use `self.update_state()` for both SUCCESS and FAILURE
3. **Consistent Returns**: Return `result.model_dump_json()` for JSON format
4. **Enterprise Logging**: Use `LoggerRegistry.get_infrastructure_logger("celery")`
5. **Error Handling**: Proper exception logging with correlation IDs

#### **Task Status Endpoint Integration**

The `/api/v1/processing/status/{job_id}` endpoint relies on proper Celery task state management:

- **PENDING**: Task is queued but not started
- **IN_PROGRESS**: Task is actively running (set by worker)
- **SUCCESS**: Task completed successfully (result available in meta)
- **FAILURE**: Task failed with error (error details in meta)

Guidelines on how `DocumentOrchestrationService` offloads tasks to the Celery worker for background processing.

### Environment Variable and Docker Compose Standards
A strict convention for environment variables must be enforced. For example, all services must use `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` for MinIO credentials. The `docker-compose.yml` file should be the single source of truth for service configuration, and the `.env` file should only contain the values for these variables. This avoids the kind of `AccessDenied` errors we encountered.

### Debugging and Observability

#### **Common Issues and Solutions**

**1. Pipeline Status Shows "in_progress" Despite Completion**

**Symptoms:**
- Celery logs show successful pipeline completion
- Status endpoint returns `{"status":"in_progress","result":null,"error":null}`
- Task appears stuck in PENDING state

**Root Cause:** Variable scope issues in celery worker or missing state updates

**Solution:**
```python
# ✅ CORRECT - Initialize result before try block
result = None
try:
    result = loop.run_until_complete(main())
    self.update_state(state='SUCCESS', meta={'result': result.model_dump_json()})
    return result.model_dump_json()
except Exception:
    self.update_state(state='FAILURE', meta={'error': 'Pipeline execution failed'})
    raise
```

**2. Empty Processing Results**

**Debugging Steps:**
```bash
# Check celery worker logs
docker compose logs celery-worker

# Check API service logs
docker compose logs api

# Check MinIO connectivity
docker compose logs minio
```

**3. Service Connection Errors**

**Common Environment Variable Issues:**
- Ensure `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` are consistent across services
- Verify `OLLAMA_BASE_URL` points to correct service
- Check Redis connection settings for Celery

#### **Log Inspection Commands**

```bash
# View recent logs (recommended)
docker compose logs api
docker compose logs celery-worker
docker compose logs minio

# Check service status
docker compose ps

# Restart specific service
docker compose restart celery-worker
```

**⚠️ NEVER use `docker compose logs -f api` - use `docker compose logs api` instead**

## **Testing DAG Pipeline with Sample Documents**

### **Step-by-Step Testing Guide**

**Prerequisites:**
```bash
# Ensure services are running
docker compose ps

# Check service health
curl -X GET "http://localhost:8000/api/v1/health/health"
# Expected: {"status":"ok"}
```

**Test 1: PDF Document Analysis (Full DAG)**
```bash
# Step 1: Submit PDF for processing
curl -X POST "http://localhost:8000/api/v1/processing/run" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample-invoice.pdf" \
  -F "pipeline_name=advanced_pdf_analysis_dag"

# Expected Response: {"job_id":"<celery-task-id>"}
# Save the job_id for status checking
```

**Test 2: Monitor Processing Status**
```bash
# Check initial status (should be "in_progress")
curl -X GET "http://localhost:8000/api/v1/processing/status/<job_id>"

# Expected: {"status":"in_progress","result":null,"error":null}

# Wait 10-30 seconds for processing, then check again
curl -X GET "http://localhost:8000/api/v1/processing/status/<job_id>"

# Expected Final Result:
# {
#   "status": "success",
#   "result": {
#     "job_id": "<correlation-id>",
#     "status": "success",
#     "results": [
#       {"processor_name": "pdf_extraction_processor", "status": "success", ...},
#       {"processor_name": "ocr_processor", "status": "success", ...},
#       {"processor_name": "vlm_processor", "status": "success", ...}
#     ],
#     "final_output": {
#       "document_id": "<document-hash>",
#       "pages": [...],
#       "document_level_results": {...}
#     }
#   },
#   "error": null
# }
```

**Test 3: Verify Log Correlation**
```bash
# Check celery worker logs for ID mapping
docker compose logs celery-worker | grep -E "(celery_task_id|correlation_id)"

# Look for entries like:
# "celery_task_id": "<job_id>", "correlation_id": "<correlation_id>"
```

**Expected Processing Timeline:**
1. **0-2s**: PDF extraction (synchronous) - converts PDF to images
2. **2-15s**: OCR processing (parallel) - extracts text from images
3. **2-30s**: VLM analysis (parallel) - AI analysis of images
4. **30s+**: Result aggregation and completion

**Troubleshooting:**
- **Status stuck "in_progress"**: Check celery worker logs for errors
- **"failed" status**: Check error message in response for details
- **No response**: Verify services are running and accessible

### Processor Result Contracts
To complement the new pipeline logic, there should be a formal contract that defines the expected output formats for each type of processor. This will ensure that any new processor developed for the platform will integrate seamlessly into the processing pipeline. For example, a processor that extracts multiple images from a document should return a list of `DocumentPayload` objects.

### The Role of `DocumentOrchestrationService`
The documentation should clarify the central role of the `DocumentOrchestrationService`. It acts as the entry point for all document processing, handling file storage, and orchestrating the `ProcessingPipeline`.

### Pipeline Technical Logic & Execution Model

The core of the application is the `ProcessingPipeline`, an engine designed around a dynamic, **"Configuration as Data"** architecture. This principle separates the *what* (the business process defined in a JSON object) from the *how* (the stable, underlying execution logic).

Pipeline definitions are stored as JSON files in the `src/app/engine_templates/` directory. Each JSON file defines a sequence of processors to be executed and specifies the execution model for the entire pipeline.

The engine supports two primary execution models, controlled by the `execution_mode` flag in the pipeline's JSON template:

1.  **`simple` (Synchronous, Linear Execution)**: For immediate, low-latency processing. The API executes the pipeline steps sequentially in a blocking fashion and returns the results directly to the client in a single HTTP response. This is ideal for quick, interactive tasks.

2.  **`dag` (Asynchronous, Graph Execution)**: For complex, long-running tasks. The API dispatches the entire pipeline to a background Celery worker, immediately returning a `job_id`. This allows for non-blocking, parallel execution of steps defined as a Directed Acyclic Graph (DAG). The client can then poll a separate endpoint to check the job's status and retrieve the results upon completion.

This hybrid model optimizes for both performance and scalability, using the appropriate execution strategy based on the pipeline's complexity and expected runtime.

---

#### **`simple` Mode: Synchronous, Linear Pipelines**

In `simple` mode, the pipeline is defined as a linear array of processor steps. The engine executes these steps sequentially, ensuring the output of one step is passed as the input to the next.

**Syntax:**
```json
{
  "name": "pdf_to_text_sync",
  "description": "Synchronously extracts text from a PDF by converting pages to images and then running OCR.",
  "execution_mode": "simple",
  "pipeline": [
    {
      "name": "pdf_extraction_processor"
    },
    {
      "name": "ocr_processor"
    }
  ]
}
```
- `execution_mode`: Must be set to `"simple"`.
- `pipeline`: An array of processor objects to be executed in order.

---

#### **`dag` Mode: Asynchronous, Parallel Pipelines**

In `dag` mode, the pipeline is defined as a graph of nodes, enabling both sequential and parallel execution. This is essential for complex workflows and performance optimization.

**Real-World Example: PDF Document Analysis**
```
PDF Input → [PDF Extraction] → Images → [OCR + VLM Analysis] → Final Results
           (synchronous)              (parallel/asynchronous)
```

**Template: `advanced_pdf_analysis_dag.json`**
```json
{
  "name": "advanced_pdf_analysis_dag",
  "description": "Extracts images from PDF, then runs OCR and VLM analysis in parallel.",
  "execution_mode": "dag",
  "pipeline": {
    "nodes": [
      {
        "id": "extract_images",
        "processor": "pdf_extraction_processor",
        "params": {
          "resolution": 300,
          "image_format": "PNG"
        }
      },
      {
        "id": "run_ocr",
        "processor": "ocr_processor",
        "dependencies": ["extract_images"],
        "params": {
          "language": "eng",
          "dpi": 300,
          "page_segmentation_mode": 3,
          "ocr_engine_mode": 3
        }
      },
      {
        "id": "analyze_with_vlm",
        "processor": "vlm_processor",
        "dependencies": ["extract_images"],
        "params": {
          "prompt": "give key data in JSON format",
          "temperature": 0.5,
          "max_tokens": 1024,
          "model": "qwen2.5vl:3b"
        }
      }
    ]
  }
}
```

**DAG Execution Flow:**
1. **Level 0**: `extract_images` (pdf_extraction_processor) - Runs first, converts PDF to images
2. **Level 1**: `run_ocr` + `analyze_with_vlm` - Run in parallel after images are extracted
3. **Result**: Document-centric output with OCR text and VLM analysis combined

**Key DAG Concepts:**
- `execution_mode`: Must be set to `"dag"`
- `pipeline.nodes`: Array of node objects defining processing steps
- `id`: Unique identifier for each node
- `dependencies`: Array of node `id`s that must complete before this node starts
- **Parallel Execution**: Nodes with same dependency run simultaneously
- **Job Status**: Remains "in_progress" until entire DAG completes

#### Enterprise-Grade DAG Execution

To ensure the `dag` engine is robust, scalable, and reliable, the following principles are enforced:

1.  **Data Integrity via Namespacing**: To prevent data collisions from parallel branches, the results of each dependency are namespaced by their `id`. A processor must access a dependency's output via `args['dependencies']['<dependency_id>']`. This guarantees predictable data flow.

2.  **Resource Management with Concurrency Limits**: To prevent resource exhaustion, the engine uses an `asyncio.Semaphore` to limit the number of concurrent tasks. This `max_concurrency` is a configurable parameter, ensuring system stability under heavy load.

### Core Architectural Patterns

-   **`ProcessorFactory`**: A secure factory is the **only** mechanism for creating processor instances from the configuration. It uses a strict, hard-coded allow-list to prevent arbitrary code execution.
-   **Hexagonal Architecture**: The pipeline core is decoupled from external systems (APIs, databases) via "ports and adapters," ensuring domain logic is pure and testable.
-   **Standardized Data Contracts**: All data passed between processors **must** adhere to Pydantic models (`DocumentPayload`, `ProcessorResult`) to ensure type safety and a consistent, auditable data flow.
-   **Composite Orchestration**: Specialized processors, like `EnhancedPdfProcessor`, act as sub-orchestrators, managing and executing their own sub-pipelines.

## UI related Logic
When a Celery worker completes a task (or even a significant step within a task), it will publish a status update to a Redis Pub/Sub channel.
Our API service will listen to this Redis channel. When it receives a message, it will push that message through the appropriate WebSocket directly to the UI in real-time.

When the /pipelines/run endpoint creates a job, it will store metadata: job_id, user_id, status, pipeline_name, created_at, etc.
The Celery worker will update this record as it works on the job: status changes to IN_PROGRESS, started_at is set, and finally, status becomes SUCCESS or FAILURE with the completed_at timestamp and a reference to the stored results.

Each piece of data will be linked back to its source (document_id, image_id).
For example, we could have an analysis_results table with columns for document_id, processor_name, result_data (as JSONB), etc.

### Enterprise Evolution Roadmap
To meet future enterprise-scale demands, the pipeline architecture is designed to evolve to include:

Advanced Workflow Orchestration (DAGs): Transition from linear chains to Directed Acyclic Graphs to support parallel execution and conditional branching, enabling more complex business logic.
Enhanced Resilience: Implement configurable Retry mechanisms for transient errors and Circuit Breakers to prevent cascading failures when interacting with external services.
Centralized State Management: Introduce a PipelineContext object to manage the inputs and outputs of each step explicitly, preventing state collisions and improving data flow traceability.
Asynchronous Task Execution: Integrate a task queue (e.g., Celery) to run long-running pipelines in the background, ensuring the API remains responsive and providing a robust mechanism for managing jobs and notifying users upon completion.

## DONTS
NEVER USE ANY NEW LIBRARY OR LIBRARY THAT IS NOT IN THE REQUIREMENTS FILES
never use paths like sys.path.insert(0, \'c:\\\\Users\\\\HP\\\\MyDrive\\\\Repos\\\\git_saqie\\\\doc_intelligence\\\\src\')
remove all the occurances of sys.path.insert(0, \'c:\\\\Users\\\\HP\\\\MyDrive\\\\Repos\\\\git_saqie\\\\doc_intelligence\\\\src\') from the codebase.

## Detailed Testing Strategy

A comprehensive testing strategy will be implemented to ensure the quality and reliability of the application.

- **Testing Pyramid**: The project will follow the testing pyramid model, with a large number of unit tests, a smaller number of integration tests, and a small number of end-to-end tests.
- **Mocking**: The project will use a mocking library (e.g., `unittest.mock`) to mock external dependencies in unit tests.
- **Test Data Management**: Test data will be managed using a combination of test data factories (e.g., `factory-boy`) and database fixtures.
- **Contract Testing**: The project will use contract testing (e.g., Pact) to ensure that the API conforms to the expected contract.





- **Enterprise Logging**: All services use the `LoggerRegistry` pattern with hierarchical naming (`api.{component}`, `service.{name}`, `processor.{type}`, `infrastructure.{component}`). All log entries include correlation IDs for distributed tracing and follow structured JSON format for automated analysis.
- **Metrics**: All services expose a `/metrics` endpoint providing performance and operational metrics in Prometheus exposition format.
- **Distributed Tracing**: The application uses correlation IDs and structured logging for request tracking across services. Future enhancement will include OpenTelemetry integration.





Application configuration will be managed using a combination of environment variables and a Pydantic-based settings model to ensure a secure and consistent configuration approach.

- **Environment Variables**: All configuration values will be provided via environment variables. This ensures that no sensitive information is hard-coded in the application.
- **Pydantic Settings Model**: A Pydantic `BaseSettings` model will be used to load and validate all environment variables. This provides a single source of truth for all configuration values and ensures that the application will not start if any required configuration is missing.
- **Secrets Management**: All secrets (e.g., database passwords, API keys) will be managed using a dedicated secrets management solution (e.g., HashiCorp Vault, AWS Secrets Manager). The application will retrieve secrets from the secrets manager at runtime.



Always prioritize enterprise integration, long-term maintainability, developer productivity, and feature completeness in that order.

## Enterprise API Endpoints
This section provides a detailed technical overview of the API endpoints, their functional purpose, and their data flows. The architecture is designed to be enterprise-grade, emphasizing scalability, discoverability, and operational transparency.

---

### **I. Core Processing & Job Management**

These endpoints form the backbone of the document processing engine, handling workflow execution and status tracking.

#### **`POST /api/v1/processing/run`**

*   **Functional Purpose**: This is the single, universal entry point for initiating all document processing workflows. It is designed to be highly flexible, supporting both immediate (synchronous) and long-running (asynchronous) tasks based on the pipeline's configuration.
*   **Architectural Role**: Acts as the primary "command" endpoint in a CQRS-like pattern. It accepts a processing request, validates it, and then dispatches it for execution according to the defined `execution_mode`.
*   **Technical Flow**:
    1.  **Request Reception**: The endpoint receives a `multipart/form-data` request containing:
        *   `file`: The raw document (e.g., PDF, PNG, JPEG).
        *   `pipeline_name`: A string identifier for the desired engine template (e.g., `"pdf_to_text_sync"`).
    2.  **Pipeline Loading**: The endpoint reads the corresponding JSON file (e.g., `pdf_to_text_sync.json`) from the `src/app/engine_templates/` directory. It inspects the `execution_mode` field within the template.
    3.  **Execution Dispatch**:
        *   **Asynchronous (`execution_mode: "dag"`)**:
            a. The pipeline configuration and file data are dispatched to a Celery worker via the `run_pipeline_task.delay()` method.
            b. The Celery task returns a unique `job_id`.
            c. The endpoint immediately returns a `202 ACCEPTED` response with the `job_id`.
        *   **Synchronous (`execution_mode: "simple"`)**:
            a. A `ProcessorFactory` instance is created.
            b. The `ProcessingPipeline` is instantiated with the pipeline configuration and the `ProcessorFactory`.
            c. The pipeline is executed directly within the API process. The request is blocked until completion.
            d. The final `ProcessorResult` is returned directly in the response body with a `200 OK` status.

---

#### **`GET /api/v1/processing/tasks/{task_id}`**

*   **Functional Purpose**: Provides a mechanism for clients to poll for the status and results of an asynchronously executed job (`dag` mode).
*   **Architectural Role**: Serves as the primary "query" endpoint for asynchronous tasks, allowing clients to track the lifecycle of a long-running process without maintaining a persistent connection.
*   **Technical Flow**:
    1.  **Request Reception**: The endpoint receives the `task_id` (a UUID) from the URL path.
    2.  **Data Retrieval**: It performs a lookup in the task data store for the entry matching the `task_id`.
    3.  **Status Response**:
        *   If the task is found, it returns a `200 OK` with the full task metadata, including `status` (`PENDING`, `IN_PROGRESS`, `SUCCESS`, `FAILURE`), timestamps, and, if completed, a reference to the results.
        *   If no task matches the ID, it returns a `404 NOT FOUND`.

---

### **II. Workflow & Capability Discovery**

These endpoints make the system's capabilities self-describing, allowing clients and UIs to dynamically adapt to the available processing workflows and components.

#### **`GET /api/v1/pipelines`**

*   **Functional Purpose**: Allows clients to discover all available, pre-defined processing workflows.
*   **Architectural Role**: Promotes loose coupling and service discovery. UIs and other clients can use this endpoint to build dynamic menus of processing options, rather than hard-coding them.
*   **Technical Flow**:
    1.  The endpoint scans the `src/app/engine_templates/` directory for all `*.json` files.
    2.  It reads each file, extracts key metadata (like `name` and `description`), and compiles them into a list.
    3.  Returns a `200 OK` with a JSON array of the available pipeline definitions.

---

#### **`GET /api/v1/pipelines/{pipeline_name}`**

*   **Functional Purpose**: Provides the detailed, underlying configuration of a specific pipeline.
*   **Architectural Role**: Offers transparency into the "Configuration as Data" model. It allows developers and advanced users to understand exactly which processors and parameters are used in a given workflow.
*   **Technical Flow**:
    1.  Receives the `pipeline_name` from the URL path.
    2.  Constructs the full path to the template file (e.g., `src/app/engine_templates/{pipeline_name}.json`).
    3.  Reads the JSON file and returns its full content with a `200 OK` status.
    4.  Returns a `404 NOT FOUND` if the file does not exist.

---

#### **`GET /api/v1/processors`**

*   **Functional Purpose**: Lists all individual, granular processing components (the \"building blocks\") available in the system.
*   **Architectural Role**: Supports the \"pipeline as code\" and custom workflow construction use cases. It provides the palette of available tools for building new engine templates.
*   **Technical Flow**:
    1.  It leverages the `ProcessorFactory`, which maintains a registry of all `BaseProcessor` implementations.
    2.  It introspects this registry to get the name and default configuration schema for each registered processor.
    3.  Returns a `200 OK` with a JSON array describing each available processor.

---

#### **`GET /api/v1/preprocessing/steps`**

*   **Functional Purpose**: Lists all available preprocessing steps.
*   **Architectural Role**: Allows clients to discover the available image enhancement and correction operations that can be used within the `ImagePreprocessingProcessor`.
*   **Technical Flow**:
    1.  The endpoint returns a hard-coded list of the available preprocessing steps.
    2.  Returns a `200 OK` with a JSON array of the available preprocessing steps.

---

### **III. System Observability**

These endpoints provide critical visibility into the health and performance of the service, adhering to enterprise monitoring standards.

#### **`GET /api/v1/health`**

*   **Functional Purpose**: A simple, unauthenticated endpoint to verify that the API service is running and responsive.
*   **Architectural Role**: Essential for load balancers, container orchestrators (like Kubernetes or Docker Swarm), and uptime monitoring tools to perform health checks.
*   **Technical Flow**:
    1.  The endpoint is configured to be accessible without any authentication.
    2.  Upon being hit, it immediately returns a `200 OK` response with a simple JSON body like `{\"status\": \"ok\"}`.
    3.  Future enhancements will include checks for connectivity to downstream dependencies like Redis and MinIO.

---

#### **`GET /api/v1/metrics`**

*   **Functional Purpose**: Exposes a wide range of performance and operational metrics in the Prometheus exposition format.
*   **Architectural Role**: The primary integration point for enterprise monitoring and alerting systems. It provides the raw data needed to build dashboards and set up alerts for latency, error rates, resource usage, and custom business KPIs.
*   **Technical Flow**:
    1.  The `prometheus-fastapi-instrumentator` library is configured as a middleware for the FastAPI application.
    2.  It automatically tracks standard metrics for all requests (e.g., `http_requests_latency_seconds`, `http_requests_total`).
    3.  Custom metrics (e.g., `pipeline_execution_time`, `processor_success_total`) are implemented using the Prometheus client library and incremented within the application logic.
    4.  When scraped by a Prometheus server, the endpoint returns a `200 OK` with the metrics in the plain-text Prometheus format.