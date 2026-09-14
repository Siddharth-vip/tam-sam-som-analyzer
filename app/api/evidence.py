from typing import Any, Dict, List, Union
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from app.fetching.models import FetchedSource, FetchRequest
from app.schemas.discovery import DiscoveryResponse, ResearchQuery
from app.schemas.evidence import EvidenceItem
from app.schemas.extraction import (
    ExtractedEvidenceCandidate,
    ExtractionRequest,
    ExtractionResponse,
)
from app.schemas.validation import (
    EvidenceValidationResult,
    TriangulationRequest,
    TriangulationResult,
)
from app.services.discovery_service import (
    DiscoveryService,
    DiscoveryServiceException,
    get_discovery_service,
)
from app.services.evidence_service import (
    EvidenceService,
    EvidenceValidationException,
    get_evidence_service,
)
from app.services.extraction_service import (
    EvidenceExtractionService,
    get_extraction_service,
)
from app.services.fetch_service import (
    SourceFetchService,
    get_fetch_service,
)
from app.services.validation_service import (
    EvidenceValidationService,
    get_validation_service,
)

router = APIRouter(prefix="/evidence", tags=["Market Evidence"])


@router.post(
    "/validate",
    response_model=Union[EvidenceValidationResult, EvidenceItem],
    status_code=status.HTTP_200_OK,
    summary="Validate and normalize an evidence candidate or record",
    description=(
        "Validates the structure, epistemic status, source traceability, and domain integrity "
        "of a single ExtractedEvidenceCandidate or EvidenceItem according to the "
        "UNKNOWN != ASSUMED != EXTRACTED != VALIDATED != VERIFIED rule."
    ),
    responses={
        200: {"description": "Evidence item or candidate successfully validated."},
        422: {"description": "Validation error in evidence item structure or domain rules."},
    },
)
def validate_evidence(
    item: Union[ExtractedEvidenceCandidate, EvidenceItem],
    evidence_service: EvidenceService = Depends(get_evidence_service),
    validation_service: EvidenceValidationService = Depends(get_validation_service),
) -> Union[EvidenceValidationResult, EvidenceItem]:
    """Validate and normalize a market research evidence candidate or item."""
    try:
        if isinstance(item, ExtractedEvidenceCandidate):
            return validation_service.validate_candidate(item)
        return evidence_service.validate_evidence(item)
    except (EvidenceValidationException, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error validating evidence: {exc}",
        ) from exc


@router.post(
    "/triangulate",
    response_model=TriangulationResult,
    status_code=status.HTTP_200_OK,
    summary="Triangulate, deduplicate, and verify extracted evidence candidates",
    description=(
        "Executes deterministic multi-source triangulation on a collection of extracted evidence candidates. "
        "Identifies duplicates, detects conflicting statistics across independent sources, and elevates "
        "candidates supported by 2+ independent domains to VERIFIED lifecycle status."
    ),
    responses={
        200: {"description": "Triangulation completed with verified, duplicate, and conflict classifications."},
        422: {"description": "Validation error in candidates payload."},
        500: {"description": "Unexpected error during multi-source triangulation."},
    },
)
def triangulate_evidence(
    payload: Union[List[ExtractedEvidenceCandidate], TriangulationRequest],
    validation_service: EvidenceValidationService = Depends(get_validation_service),
) -> TriangulationResult:
    """Validate, deduplicate, detect conflicts, and triangulate extracted evidence candidates."""
    try:
        candidates = payload.candidates if isinstance(payload, TriangulationRequest) else payload
        return validation_service.triangulate_evidence(candidates)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during evidence triangulation: {exc}",
        ) from exc


@router.post(
    "/discover",
    response_model=DiscoveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover potential external market evidence sources",
    description=(
        "Executes a structured research query against discovery providers to identify candidate "
        "evidence documents. Discovered sources are tagged with lifecycle_stage='discovered' "
        "and are NOT considered verified evidence."
    ),
    responses={
        200: {"description": "Discovery query executed and candidate sources returned."},
        422: {"description": "Validation error in structured research query."},
        500: {"description": "Discovery service execution error."},
    },
)
async def discover_market_evidence(
    query: ResearchQuery,
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryResponse:
    """Discover candidate market evidence sources from external indices."""
    try:
        return await service.discover_sources(query)
    except DiscoveryServiceException as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during source discovery: {exc}",
        ) from exc


@router.post(
    "/fetch",
    response_model=FetchedSource,
    status_code=status.HTTP_200_OK,
    summary="Safely fetch and sanitize content from a source URL",
    description=(
        "Fetches external document content with SSRF protection, size limits, and timeout guards. "
        "Content is cleaned into plain text and returned with lifecycle_stage='fetched'."
    ),
    responses={
        200: {"description": "Document fetch attempt completed (check fetch_status for outcome)."},
        422: {"description": "Validation error in fetch request parameters."},
        500: {"description": "Unexpected error during document retrieval."},
    },
)
async def fetch_source_document(
    request: FetchRequest,
    service: SourceFetchService = Depends(get_fetch_service),
) -> FetchedSource:
    """Fetch and sanitize external source document content."""
    try:
        return await service.fetch_source(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during content fetch: {exc}",
        ) from exc


@router.post(
    "/extract",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract candidate factual evidence metrics from fetched source text",
    description=(
        "Parses candidate metrics, numbers, units, and temporal data from fetched content. "
        "Extracted candidates are tagged with lifecycle_stage='extracted' and are NOT yet verified."
    ),
    responses={
        200: {"description": "Extraction completed and candidates returned."},
        422: {"description": "Validation error in extraction request parameters."},
        500: {"description": "Unexpected error during evidence extraction."},
    },
)
def extract_evidence_from_source(
    request: ExtractionRequest,
    service: EvidenceExtractionService = Depends(get_extraction_service),
) -> ExtractionResponse:
    """Extract candidate evidence metrics from fetched source text."""
    try:
        return service.extract_evidence_from_source(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during evidence extraction: {exc}",
        ) from exc
