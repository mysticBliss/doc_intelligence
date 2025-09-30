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
from app.core.config import config
from app.core.limiter import limiter
from app.domain.models import (
    DIPRequest,
    DIPResponse,
    DIPChatRequest,
    DIPChatResponse,
    ChatMessage,
    ChatRequest,
    PipelineTemplate,
    ImageProcessingRequest,
    ImageProcessingResponse,
)
from app.infrastructure.dip_client import DIPClient, get_dip_client, DIPClientPort
from app.services.pdf_processor import PDFProcessor
from app.services.factory import get_pdf_processor, get_template_service, get_image_processing_service
from app.services.template_service import TemplateService
from app.services.image_processing_service import ImageProcessingService
from app.core.context import get_request_context, get_correlation_id
import base64
import time
from typing import List

import asyncio

import httpx
import structlog

router = APIRouter()
logger = structlog.get_logger(__name__)

@router.post("/images/process", response_model=ImageProcessingResponse)
@limiter.limit("30/minute")
async def process_image(
    request: Request,
    body: ImageProcessingRequest,
    image_service: ImageProcessingService = Depends(get_image_processing_service),
):
    """
    Processes a single image through a dynamic pipeline of processing gears.

    This endpoint provides a flexible way to apply various processing steps
    (e.g., preprocessing, OCR, VLM analysis) to an image by specifying them
    in the `gears_to_run` list.
    """
    try:
        # The service layer handles the core logic, making the endpoint a lean adapter.
        response = image_service.process_image(body)
        return response
    except ValueError as e:
        # Handle specific, known errors, such as an unknown gear
        logger.warn("Image processing failed due to invalid gear request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("An unexpected error occurred during image processing", error=str(e))
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


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
    dip_client: DIPClientPort = Depends(get_dip_client),
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
    dip_client: DIPClientPort = Depends(get_dip_client),
    pdf_processor: PDFProcessor = Depends(get_pdf_processor),
    image_service: ImageProcessingService = Depends(get_image_processing_service),
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
        log.info(
            f"Successfully converted {len(image_bytes_list)} pages to images.",
            correlation_id=get_correlation_id(),
        )

        # --- Natively Asynchronous Image Preprocessing ---
        tasks = []
        document_id = get_correlation_id() if len(image_bytes_list) > 1 else None

        for img_bytes in image_bytes_list:
            req = ImageProcessingRequest(
                image_data=base64.b64encode(img_bytes).decode("utf-8"),
                gears_to_run=["image_preprocessor"],
                preprocessing_steps=pipeline_steps.split(',') if pipeline_steps else None,
                document_id=document_id,
            )
            tasks.append(image_service.process_image(req))

        # Concurrently run all processing tasks
        img_proc_responses: List[ImageProcessingResponse] = await asyncio.gather(*tasks)

        processed_images_b64 = [
            gear_result.result_data["processed_image_b64"]
            for response in img_proc_responses
            if response.results
            for gear_result in response.results
            if gear_result.gear_name == "image_preprocessor"
        ]

        # Create a new DIPRequest with the processed images
        dip_request = DIPRequest(
            model=model_name,
            prompt=text_prompt,
            images=processed_images_b64,
            stream=False,
        )

        response = await dip_client.generate(dip_request)
        response.request_context = get_request_context()

        if document_id:
            response.document_id = document_id

        log.info(
            "Successfully preprocessed images and generated response.",
            correlation_id=get_correlation_id(),
        )
        return response

    except httpx.ReadTimeout:
        log.error("Request to DIP service timed out.")
        raise HTTPException(status_code=504, detail="Request to DIP service timed out.")
    except Exception as e:
        log.error(f"An unexpected error occurred in process_pdf: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@router.post("/chat/stream", response_model=DIPChatResponse)
@limiter.limit("20/minute")
async def chat_stream(
    request: Request,
    body: ChatRequest,
    dip_client: DIPClientPort = Depends(get_dip_client),
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

    except httpx.HTTPStatusError as e:
        log.error(
            f"HTTP error occurred while communicating with DIP service: {e.response.text}",
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