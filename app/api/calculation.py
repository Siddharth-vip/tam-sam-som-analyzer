from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from app.schemas.calculation import CalculationInput, CalculationReport
from app.services.calculation_service import (
    CalculationService,
    CalculationServiceException,
    get_calculation_service,
)

router = APIRouter(prefix="/market", tags=["Market Calculation"])


@router.post(
    "/calculate",
    response_model=CalculationReport,
    status_code=status.HTTP_200_OK,
    summary="Calculate TAM, SAM, and SOM using deterministic top-down and bottom-up models",
    description=(
        "Executes auditable, deterministic market-sizing calculations using verified evidence "
        "and explicit assumptions. Strictly rejects unvalidated/discovered evidence, enforces "
        "the SOM safety rule (no arbitrary percentages), performs cross-method divergence analysis, "
        "and propagates uncertainty intervals without numerical fabrication."
    ),
    responses={
        200: {"description": "Calculation report generated with full audit trail and methodology comparisons."},
        422: {"description": "Validation error in calculation input structure or domain bounds."},
        500: {"description": "Unexpected error during market sizing calculation."},
    },
)
def calculate_market_sizing(
    request: CalculationInput,
    service: CalculationService = Depends(get_calculation_service),
) -> CalculationReport:
    """Calculate TAM, SAM, and SOM from validated evidence and explicit assumptions."""
    try:
        return service.generate_report(request)
    except (CalculationServiceException, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during market calculation: {exc}",
        ) from exc
