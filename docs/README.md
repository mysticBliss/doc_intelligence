# Technical Documentation

This document provides a detailed technical overview of the Document Intelligence Platform, including its High-Level Design (HLD) and Low-Level Design (LLD).

## 1. High-Level Design (HLD)

### 1.1. System Overview

The Document Intelligence Platform is a web service designed to process and analyze documents, leveraging a large language model (LLM) to provide insights and generate content.

### 1.2. Architectural Style

The system is built upon a **Hexagonal Architecture (Ports & Adapters)**, which isolates the core application logic from external dependencies such as the web framework, database, and third-party services.

### 1.3. Key Components

- **Application Core:** Contains the primary business logic and domain models.
- **Web API (FastAPI):** Exposes the application's functionality via a RESTful API.
- **DIP Client:** An adapter that encapsulates communication with the external Document Intelligence Platform (DIP).
- **PDF Processor:** A service for parsing and processing PDF documents.

### 1.4. System Diagram

```mermaid
graph TD
    A[User] --> B{Web API (FastAPI)};
    B --> C[Application Core];
    C --> D[DIP Client];
    D --> E[External DIP Service];
    C --> F[PDF Processor];
```

## 2. Low-Level Design (LLD)

### 2.1. Domain Models (`app/domain/models.py`)

- **`DIPRequest`**: Represents a request to the DIP for text generation.
- **`DIPResponse`**: Represents a response from the DIP for text generation.
- **`DIPChatRequest`**: Represents a request to the DIP for chat-based interaction.
- **`DIPChatResponse`**: Represents a response from the DIP for chat-based interaction.
- **`RequestContext`**: Contains metadata for a single request, including a `correlation_id`.

### 2.2. API Endpoints (`app/api/endpoints.py`)

- **`POST /api/generate`**: Accepts a `DIPRequest` and returns a `DIPResponse`.
- **`POST /api/process_pdf`**: Accepts a PDF file and a text prompt, and returns a `DIPChatResponse`.

### 2.3. Infrastructure (`app/infrastructure`)

- **`DIPClient`**: A client for interacting with the external DIP service. It includes methods for `generate` and `chat`.

### 2.4. Services (`app/services`)

- **`PDFProcessor`**: A service that converts PDF files into a series of images for processing by the DIP.

### 2.5. Core Components (`app/core`)

- **`context.py`**: Manages the request context, including the `correlation_id`.
- **`logging.py`**: Configures structured logging and injects the `correlation_id` into log records.
- **`main.py`**: The main entry point of the application, which sets up the FastAPI app, middleware, and routes.

### 2.6. Model Provisioning

The provisioning of the required models is handled by the `ollama` service, as defined in the `docker-compose.yml` file. This approach decouples the application from the model management process, which is a key aspect of the Hexagonal Architecture.

The `ollama` service is configured to automatically pull the required model upon startup. This is achieved by adding a `command` to the service definition in the `docker-compose.yml` file:

```yaml
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ./model:/root/.ollama
    container_name: ollama
    command: /bin/sh -c "ollama serve & ollama pull qwen2.5vl:3b && fg"
```

#### Steps to Execute and Verify

1.  **Start the Services:**
    Open a terminal at the root of the project and run:
    ```bash
    docker compose up --build
    ```

2.  **Monitor the Logs:**
    Observe the logs from the `ollama` service to confirm that the model is being downloaded.

3.  **Verify the Model:**
    Once the services are running, open another terminal and run the following command to verify that the model is available:
    ```bash
    docker exec -it ollama ollama list
    ```