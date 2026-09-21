from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.business import BusinessAnalysis, BusinessIdeaRequest
from app.schemas.classification import B2BSaaSClassification
from app.services.classification_service import (
    B2BSaaSClassificationService,
    get_classification_service,
)
from app.services.llm_service import (
    LLMConnectionError,
    LLMResponseError,
    LLMTimeoutError,
    OllamaLLMService,
    get_llm_service,
)

router = APIRouter(prefix="/business", tags=["Business Analysis"])


@router.post(
    "/analyze",
    response_model=BusinessAnalysis,
    status_code=status.HTTP_200_OK,
    summary="Analyze an unstructured business idea",
    description=(
        "Extract structured business information (industry, product, target customer, geography, "
        "business model, pricing model, customer problem, value proposition) from an unstructured "
        "business idea using local Ollama LLM extraction."
    ),
    responses={
        200: {"description": "Structured business analysis returned successfully."},
        422: {"description": "Invalid input: empty or malformed business idea."},
        502: {"description": "LLM returned an invalid or unparseable response."},
        503: {"description": "Ollama service unavailable or unreachable."},
        504: {"description": "LLM inference request timed out."},
    },
)
async def analyze_business_idea(
    request: BusinessIdeaRequest,
    llm_service: OllamaLLMService = Depends(get_llm_service),
) -> BusinessAnalysis:
    """Analyze a business idea and return structured attributes."""
    try:
        return await llm_service.analyze_business_idea(request.business_idea)
    except LLMConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except LLMTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        ) from exc
    except LLMResponseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post(
    "/classify",
    response_model=B2BSaaSClassification,
    status_code=status.HTTP_200_OK,
    summary="Classify a business idea into the B2B SaaS taxonomy",
    description=(
        "Semantically classify a business concept into the canonical B2B SaaS taxonomy, "
        "evaluating B2B vs B2C, SaaS vs non-SaaS, category, subcategory, buyer persona, use cases, "
        "and provenance."
    ),
    responses={
        200: {"description": "B2B SaaS classification returned successfully."},
        422: {"description": "Invalid input: empty or malformed business idea."},
        500: {"description": "Unexpected error during classification."},
    },
)
async def classify_business_idea(
    request: BusinessIdeaRequest,
    classifier: B2BSaaSClassificationService = Depends(get_classification_service),
) -> B2BSaaSClassification:
    """Classify a business idea into canonical B2B SaaS categories."""
    try:
        return await classifier.classify_business_idea(request.business_idea, allow_fallback=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during classification: {exc}",
        ) from exc

