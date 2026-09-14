from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.orchestration.events import format_sse_event
from app.orchestration.models import PipelineRequest, PipelineResult
from app.orchestration.pipeline import (
    MarketAnalysisPipeline,
    get_market_pipeline,
)

router = APIRouter(prefix="/pipeline", tags=["Pipeline Orchestration"])


@router.post(
    "/analyze",
    response_model=PipelineResult,
    status_code=status.HTTP_200_OK,
    summary="Execute end-to-end AI TAM/SAM/SOM market analysis pipeline",
    description=(
        "Orchestrates the full market sizing lifecycle: Business Idea Extraction → Research Query Generation → "
        "Evidence Discovery → Source Fetching → Evidence Extraction → Validation & Deduplication → "
        "Multi-Source Triangulation → Evidence Gate → Deterministic TAM/SAM/SOM Calculation. "
        "Strictly adheres to zero-hallucination rules and preserves complete provenance."
    ),
    responses={
        200: {"description": "Pipeline execution completed with structured market sizing report and audit trail."},
        422: {"description": "Validation error in pipeline request parameters."},
        500: {"description": "Unexpected error during pipeline execution."},
    },
)
async def analyze_market_pipeline(
    request: PipelineRequest,
    pipeline: MarketAnalysisPipeline = Depends(get_market_pipeline),
) -> PipelineResult:
    """Execute the full end-to-end TAM/SAM/SOM market analysis workflow."""
    try:
        return await pipeline.run(request)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during pipeline execution: {exc}",
        ) from exc


@router.post(
    "/analyze/stream",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    summary="Stream end-to-end TAM/SAM/SOM analysis progress via Server-Sent Events (SSE)",
    description=(
        "Executes the full market sizing workflow while streaming real-time stage progress events "
        "using standard Server-Sent Events (SSE) formatting (`data: {...}\\n\\n`)."
    ),
    responses={
        200: {"description": "Real-time SSE event stream of pipeline stage execution."},
        422: {"description": "Validation error in request parameters."},
    },
)
async def stream_market_pipeline(
    request: PipelineRequest,
    pipeline: MarketAnalysisPipeline = Depends(get_market_pipeline),
) -> StreamingResponse:
    """Stream real-time progress events for the market analysis pipeline via Server-Sent Events (SSE)."""

    async def event_generator():
        async for event in pipeline.run_with_progress(request):
            yield format_sse_event(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/history",
    status_code=status.HTTP_200_OK,
    summary="List past market analysis runs",
    description="Retrieve a paginated list of previous market analysis summaries stored in the persistence repository.",
)
async def list_pipeline_history(
    limit: int = 50,
    offset: int = 0,
    pipeline: MarketAnalysisPipeline = Depends(get_market_pipeline),
):
    """Retrieve history of previous market analysis runs."""
    try:
        items = pipeline.repository.list_all(limit=limit, offset=offset)
        total = pipeline.repository.count()
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve analysis history: {exc}",
        ) from exc


@router.get(
    "/{pipeline_id}",
    status_code=status.HTTP_200_OK,
    summary="Get previous analysis by ID",
    description="Retrieve a full stored market analysis result by its unique pipeline execution ID.",
)
async def get_pipeline_by_id(
    pipeline_id: str,
    pipeline: MarketAnalysisPipeline = Depends(get_market_pipeline),
):
    """Retrieve a specific past market analysis by pipeline ID."""
    item = pipeline.repository.get_by_id(pipeline_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Market analysis with ID '{pipeline_id}' not found.",
        )
    return item


@router.delete(
    "/{pipeline_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete previous analysis by ID",
    description="Delete a stored market analysis record from persistence.",
)
async def delete_pipeline_by_id(
    pipeline_id: str,
    pipeline: MarketAnalysisPipeline = Depends(get_market_pipeline),
):
    """Delete a specific past market analysis by pipeline ID."""
    deleted = pipeline.repository.delete(pipeline_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Market analysis with ID '{pipeline_id}' not found.",
        )
    return {"status": "deleted", "pipeline_id": pipeline_id}

