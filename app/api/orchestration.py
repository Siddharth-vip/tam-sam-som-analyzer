from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from app.schemas.orchestration import (
    OrchestrationRequest,
    OrchestrationResult,
)
from app.services.orchestration_service import (
    OrchestrationService,
    get_orchestration_service,
)

router = APIRouter(prefix="/market", tags=["Market Analysis Orchestration"])


@router.post(
    "/analyze",
    response_model=OrchestrationResult,
    status_code=status.HTTP_200_OK,
    summary="Execute end-to-end AI TAM/SAM/SOM market analysis workflow",
    description=(
        "Orchestrates the full market analysis lifecycle: Business Idea Extraction → "
        "Research Query Generation → Evidence Discovery → Source Fetching → Evidence Extraction → "
        "Validation → Deduplication + Conflict Detection + Triangulation → Evidence Gating → "
        "Deterministic TAM/SAM/SOM Calculation → Final Auditable Report."
    ),
    responses={
        200: {"description": "Market analysis executed successfully with structured sizing results."},
        422: {"description": "Invalid business idea or input validation error."},
        500: {"description": "Internal server error during analysis execution."},
    },
)
async def analyze_market(
    request: OrchestrationRequest,
    orchestrator: OrchestrationService = Depends(get_orchestration_service),
) -> OrchestrationResult:
    """Execute the complete end-to-end TAM/SAM/SOM market analysis workflow."""
    try:
        return await orchestrator.run(request)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during market analysis: {exc}",
        ) from exc
