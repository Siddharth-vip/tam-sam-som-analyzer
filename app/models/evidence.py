from dataclasses import dataclass, field
from typing import Optional

from app.schemas.evidence import ConfidenceLevel, EvidenceStatus, SourceType


@dataclass
class EvidenceRecord:
    """Domain model representing an in-memory market evidence record."""

    metric: str
    value: Optional[float] = None
    unit: Optional[str] = None
    geography: Optional[str] = None
    year: Optional[int] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    source_type: SourceType = SourceType.UNKNOWN
    source_date: Optional[str] = None
    methodology: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    evidence_status: EvidenceStatus = EvidenceStatus.UNKNOWN
    used_for: Optional[str] = None
    notes: Optional[str] = None
    metadata: dict = field(default_factory=dict)
