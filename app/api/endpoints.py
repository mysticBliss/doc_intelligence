from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Request,
    BackgroundTasks,
)
from typing import Optional
from core.config import config
from core.limiter import limiter
from domain.models import (
    DIPRequest,
    DIPResponse,
    DIPChatRequest,
    DIPChatResponse,
    ChatMessage,
    DocumentMetadata,
    AuditEvent,
    AuditEventName,
    ChatRequest,
    PipelineTemplate,
)
from infrastructure.dip_client import DIPClient, get_dip_client
from services.pdf_processor import PDFProcessor
from services.image_preprocessor import ImagePreprocessor
from services.factory import get_pdf_processor, get_image_preprocessor, get_template_service
from services.template_service import TemplateService
from core.context import get_request_context, get_correlation_id
from core.auditing import log_audit_event
import base64
import time
from datetime import datetime
from typing import List

import httpx
import structlog

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/pipeline-templates", response_model=List[PipelineTemplate])
async def get_pipeline_templates(
    template_service: TemplateService = Depends(get_template_service),
):
    """Returns a list of available preprocessing pipeline templates."""
    return template_service.get_all_templates()


@router.post("/generate", response_model=DIPResponse)
@limiter.limit("20/minute")
async def generate(
    request: Request,
    body: DIPRequest,
    dip_client: DIPClient = Depends(get_dip_client),
    pdf_processor: PDFProcessor = Depends(get_pdf_processor),
):
    body.model = config.default_model
    log = logger.bind(model=body.model)
    log.info("Received generate request")
    try:
        # --- Annotation Processing Logic ---
        if body.annotated_images:
            log.info(f"Processing {len(body.annotated_images)} annotated images.")
            processed_images = []
            for annotated_image in body.annotated_images:
                original_image_bytes = base64.b64decode(annotated_image.image_data)
                
                if not annotated_image.annotations:
                    # If there are no annotations, add the original image and continue
                    processed_images.append(base64.b64encode(original_image_bytes).decode("utf-8"))
                    continue

                # Cropping logic based on the Strategy Pattern
                for bbox in annotated_image.annotations:
                    log.info(f"Cropping image with bbox: {bbox.dict()}")
                    try:
                        cropped_image_bytes = pdf_processor.crop_image(
                            original_image_bytes, bbox
                        )
                        processed_images.append(base64.b64encode(cropped_image_bytes).decode("utf-8"))
                    except Exception as crop_error:
                        log.error("Failed to crop image", error=str(crop_error))
                        raise HTTPException(
                            status_code=400,
                            detail=f"Failed to process bounding box: {crop_error}"
                        )
            
            # Create a new DIPRequest with the processed images
            # This replaces the original annotated_images with a flat list of cropped images
            body = DIPRequest(
                model=body.model,
                prompt=body.prompt,
                images=processed_images,
                stream=body.stream
            )

        response = await dip_client.generate(body)
        response.request_context = get_request_context()
        log.info("Successfully generated response")
        return response
    except Exception as e:
        log.error("Error during generation", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process_pdf", response_model=DIPResponse)
@limiter.limit("5/minute")
async def process_pdf(
    request: Request,
    background_tasks: BackgroundTasks,
    pdf_file: UploadFile = File(...),
    text_prompt: str = Form("Describe the content of these pages."),
    page_numbers: Optional[str] = Form(None),  # Expect a comma-separated string
    pipeline_steps: Optional[str] = Form(None), # Expect a comma-separated string
    dip_client: DIPClient = Depends(get_dip_client),
    pdf_processor: PDFProcessor = Depends(get_pdf_processor),
    image_preprocessor: ImagePreprocessor = Depends(get_image_preprocessor),
):
    start_time = time.time()
    model_name = config.default_model
    log = logger.bind(filename=pdf_file.filename, model=model_name)
    log.info("Received process_pdf request")

    if pdf_file.content_type != "application/pdf":
        log.warn("Invalid file type uploaded")
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only PDFs are accepted."
        )

    pdf_contents = await pdf_file.read()
    log.info("PDF file read successfully")

    processed_page_numbers = []
    if page_numbers:
        try:
            # Convert comma-separated string to list of ints
            processed_page_numbers = [int(p.strip()) for p in page_numbers.split(',')]
            log.info(f"Processing specific pages: {processed_page_numbers}")
        except ValueError:
            log.warn("Invalid page_numbers format. Must be comma-separated integers.")
            raise HTTPException(
                status_code=400,
                detail="Invalid page_numbers format. Must be a comma-separated list of integers.",
            )

    try:
        image_bytes_list, page_metadata = pdf_processor.pdf_to_images(
            pdf_contents, page_numbers=processed_page_numbers or None
        )
        log.info(f"Successfully converted PDF to {len(image_bytes_list)} images")

        # --- Image Preprocessing ---
        pipeline = pipeline_steps.split(',') if pipeline_steps else []
        processed_image_bytes_list, processing_results = image_preprocessor.run_pipeline_on_list(
            image_bytes_list, pipeline=pipeline
        )
        log.info("Successfully preprocessed images")

    except Exception as e:
        log.error("Failed to process PDF", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {e}")

    if not processed_image_bytes_list:
        log.warn("No images could be generated from the PDF")
        raise HTTPException(
            status_code=400, detail="No images could be generated from the PDF."
        )

    encoded_images = [
        base64.b64encode(img_bytes).decode("utf-8") for img_bytes in processed_image_bytes_list
    ]

    dip_request = DIPRequest(
        model=model_name,
        prompt=text_prompt,
        images=encoded_images,
        stream=False,  # Assuming this is not a streaming response
    )

    try:
        # Route to the generate endpoint
        response = await dip_client.generate(dip_request)
        response.request_context = get_request_context()
        
        # Assign the detailed processing results to the response model
        response.processing_results = processing_results
        
        log.info("Successfully received response from DIP generate endpoint")

    except httpx.HTTPStatusError as e:
        log.error(
            "DIP service returned an error",
            status_code=e.response.status_code,
            response_text=e.response.text,
            error=str(e),
        )
        raise HTTPException(
            status_code=502,  # Bad Gateway
            detail=f"Error from DIP service: {e.response.text}",
        )
    except httpx.TimeoutException as e:
        log.error("Request to DIP service timed out", error=str(e))
        raise HTTPException(status_code=504, detail="Request to DIP service timed out.")
    except httpx.RequestError as e:
        log.error("Failed to connect to DIP service", error=str(e))
        raise HTTPException(
            status_code=503,  # Service Unavailable
            detail=f"Failed to connect to DIP service: {e}",
        )
    except Exception as e:
        log.error("An unexpected error occurred while processing the PDF", error=str(e))
        # --- Schedule Audit Event for Failure ---
        response_time_ms = (time.time() - start_time) * 1000
        audit_event = AuditEvent(
            event_name=AuditEventName.PROCESS_PDF_FAILURE,
            correlation_id=get_correlation_id(),
            timestamp=datetime.utcnow().isoformat(),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            http_method=request.method,
            endpoint_path=request.url.path,
            http_status_code=500,
            response_time_ms=response_time_ms,
            event_data={
                "file_name": pdf_file.filename,
                "file_size": len(pdf_contents),
                "error_message": str(e),
            },
        )
        background_tasks.add_task(log_audit_event, audit_event)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    # --- Schedule Audit Event ---
    response_time_ms = (time.time() - start_time) * 1000
    audit_event = AuditEvent(
        event_name=AuditEventName.PROCESS_PDF_SUCCESS,
        correlation_id=get_correlation_id(),
        timestamp=datetime.utcnow().isoformat(),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        http_method=request.method,
        endpoint_path=request.url.path,
        http_status_code=200,
        response_time_ms=response_time_ms,
        event_data={
            "file_name": pdf_file.filename,
            "file_size": len(pdf_contents),
            "page_count": len(image_bytes_list),
            "prompt": text_prompt,
            "model_used": model_name,
        },
    )
    background_tasks.add_task(log_audit_event, audit_event)

    return response


@router.post("/chat", response_model=DIPChatResponse)
@limiter.limit("20/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    dip_client: DIPClient = Depends(get_dip_client),
):
    """
    Provides a general-purpose chat endpoint.
    """
    model_name = config.default_model
    log = logger.bind(model=model_name)
    log.info("Received chat request")

    chat_request = DIPChatRequest(
        model=model_name,
        messages=[
            ChatMessage(
                role="user",
                content=body.prompt,
            )
        ],
    )

    try:
        response = await dip_client.chat(chat_request)
        response.request_context = get_request_context()
        log.info("Successfully received response from DIP")
        return response
    except httpx.HTTPStatusError as e:
        log.error(
            "DIP service returned an error",
            status_code=e.response.status_code,
            response_text=e.response.text,
            request_details=e.request.url,
        )
        raise HTTPException(
            status_code=502,  # Bad Gateway
            detail=f"Error from DIP service: {e.response.status_code} - {e.response.text}",
        )
    except Exception as e:
        log.error("Failed to get response from DIP", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get response from DIP: {e}"
        )