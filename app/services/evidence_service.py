import logging
from typing import Any, Dict, List, Optional

from app.models.evidence import EvidenceRecord
from app.schemas.evidence import (
    ConfidenceLevel,
    EvidenceItem,
    EvidenceStatus,
    SourceType,
)

logger = logging.getLogger(__name__)


class EvidenceValidationException(Exception):
    """Exception raised when an evidence item fails domain validation rules."""
    pass


class EvidenceService:
    """Service responsible for validating, normalizing, and managing market research evidence records."""

    def normalize_evidence_item(self, item: EvidenceItem) -> EvidenceItem:
        """Normalize an EvidenceItem to canonical representation."""
        data = item.model_dump()

        # If evidence status is explicitly assumed and source_type is unknown, normalize source_type to ASSUMPTION
        if data["evidence_status"] == EvidenceStatus.ASSUMED.value:
            if data["source_type"] == SourceType.UNKNOWN.value:
                data["source_type"] = SourceType.ASSUMPTION.value

        # Return newly validated and normalized model instance
        return EvidenceItem.model_validate(data)

    def validate_evidence(self, item: EvidenceItem) -> EvidenceItem:
        """Perform comprehensive domain validation on an evidence item and return the normalized record."""
        # 1. Base Pydantic schema validation is executed upon instantiation
        normalized_item = self.normalize_evidence_item(item)

        # 2. Additional domain integrity checks
        if normalized_item.evidence_status == EvidenceStatus.VERIFIED.value:
            if not normalized_item.source_name:
                raise EvidenceValidationException("Verified evidence must include an identifiable source_name.")

        if normalized_item.evidence_status == EvidenceStatus.UNKNOWN.value:
            if normalized_item.value is not None:
                raise EvidenceValidationException("Unknown evidence items cannot contain a numerical value.")

        return normalized_item

    def inspect_evidence_quality(self, item: EvidenceItem) -> Dict[str, Any]:
        """Inspect evidence item for completeness, traceability, and confidence assessment."""
        warnings: List[str] = []

        if item.evidence_status == EvidenceStatus.ASSUMED.value:
            warnings.append("Item is an unverified assumption and must be cross-checked during triangulation.")

        if item.evidence_status == EvidenceStatus.VERIFIED.value and not item.source_url:
            warnings.append("Verified item has source_name but lacks a direct source_url link.")

        if item.year is not None and item.year < 2020:
            warnings.append(f"Historical data from year {item.year} may require inflation/growth adjustment.")

        if item.value is not None and not item.geography:
            warnings.append("Numerical metric lacks an explicit geographic scope.")

        return {
            "is_verified": item.evidence_status == EvidenceStatus.VERIFIED.value,
            "is_assumed": item.evidence_status == EvidenceStatus.ASSUMED.value,
            "is_unknown": item.evidence_status == EvidenceStatus.UNKNOWN.value,
            "has_source_url": bool(item.source_url),
            "warnings": warnings,
        }

    def to_domain_record(self, item: EvidenceItem) -> EvidenceRecord:
        """Convert a validated EvidenceItem schema into an in-memory domain EvidenceRecord."""
        validated = self.validate_evidence(item)
        return EvidenceRecord(
            metric=validated.metric,
            value=validated.value,
            unit=validated.unit,
            geography=validated.geography,
            year=validated.year,
            source_name=validated.source_name,
            source_url=validated.source_url,
            source_type=SourceType(validated.source_type),
            source_date=validated.source_date,
            methodology=validated.methodology,
            confidence=ConfidenceLevel(validated.confidence),
            evidence_status=EvidenceStatus(validated.evidence_status),
            used_for=validated.used_for,
            notes=validated.notes,
        )


def get_evidence_service() -> EvidenceService:
    """Dependency provider for EvidenceService."""
    return EvidenceService()
