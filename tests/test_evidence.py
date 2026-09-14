import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models.evidence import EvidenceRecord
from app.schemas.evidence import (
    ConfidenceLevel,
    EvidenceItem,
    EvidenceStatus,
    SourceType,
)
from app.services.evidence_service import EvidenceService

client = TestClient(app)
evidence_service = EvidenceService()


# ---------------------------------------------------------------------------
# Schema & Domain Validation Unit Tests
# ---------------------------------------------------------------------------

def test_valid_verified_evidence_item() -> None:
    """TEST 1: Valid verified evidence with all source metadata passes validation."""
    item = EvidenceItem(
        metric="Number of college students in India",
        value=43000000.0,
        unit="students",
        geography="India",
        year=2025,
        source_name="Ministry of Education / AISHE",
        source_url="https://example.gov.in/aishe-report",
        source_type=SourceType.OFFICIAL_STATISTICS,
        source_date="2025-01-15",
        methodology="Annual National Higher Education Census",
        confidence=ConfidenceLevel.HIGH,
        evidence_status=EvidenceStatus.VERIFIED,
        used_for="TAM base population",
        notes="Undergraduate, postgraduate, and diploma students",
    )
    assert item.metric == "Number of college students in India"
    assert item.value == 43000000.0
    assert item.unit == "students"
    assert item.geography == "India"
    assert item.year == 2025
    assert item.source_name == "Ministry of Education / AISHE"
    assert item.evidence_status == "verified"


def test_verified_evidence_without_source_rejected() -> None:
    """TEST 2: Verified evidence without an identifiable source_name fails validation."""
    with pytest.raises(ValidationError) as exc:
        EvidenceItem(
            metric="Number of college students in India",
            value=43000000.0,
            unit="students",
            geography="India",
            year=2025,
            source_name=None,  # Missing source
            evidence_status=EvidenceStatus.VERIFIED,
        )
    assert "source_name" in str(exc.value).lower()


def test_verified_evidence_cannot_have_assumption_source_type() -> None:
    """Verified evidence cannot claim source_type = 'assumption'."""
    with pytest.raises(ValidationError) as exc:
        EvidenceItem(
            metric="Average annual subscription spend",
            value=1200.0,
            unit="INR",
            geography="India",
            source_name="Analyst estimate",
            source_type=SourceType.ASSUMPTION,
            evidence_status=EvidenceStatus.VERIFIED,
        )
    assert "assumption" in str(exc.value).lower()


def test_assumed_evidence_valid() -> None:
    """TEST 3: Assumed evidence must explicitly use evidence_status = 'assumed'."""
    item = EvidenceItem(
        metric="Estimated conversion rate of college programmers to paid users",
        value=0.03,
        unit="%",
        geography="India",
        year=2025,
        source_name="Methodology assumption",
        source_type=SourceType.ASSUMPTION,
        confidence=ConfidenceLevel.LOW,
        evidence_status=EvidenceStatus.ASSUMED,
        notes="Assumed 3% based on benchmark freemium conversion rates.",
    )
    assert item.evidence_status == "assumed"
    assert item.source_type == "assumption"


def test_assumed_evidence_cannot_claim_government_source() -> None:
    """Assumed evidence cannot claim official government sources."""
    with pytest.raises(ValidationError) as exc:
        EvidenceItem(
            metric="Target customer capture rate",
            value=0.05,
            unit="%",
            source_name="Ministry of Statistics",
            source_type=SourceType.GOVERNMENT,
            evidence_status=EvidenceStatus.ASSUMED,
        )
    assert "assumed" in str(exc.value).lower()


def test_unknown_evidence_cannot_have_numerical_value() -> None:
    """TEST 4: Unknown evidence must not contain an unsupported numerical value."""
    with pytest.raises(ValidationError) as exc:
        EvidenceItem(
            metric="Total annual expenditure on online coding courses in India",
            value=500000000.0,  # Fabricated value for unknown status
            unit="USD",
            evidence_status=EvidenceStatus.UNKNOWN,
        )
    assert "unknown" in str(exc.value).lower()


def test_valid_unknown_evidence() -> None:
    """Valid unknown evidence item with null value."""
    item = EvidenceItem(
        metric="Total annual expenditure on online coding courses in India",
        value=None,
        unit=None,
        geography="India",
        evidence_status=EvidenceStatus.UNKNOWN,
        confidence=ConfidenceLevel.UNKNOWN,
        notes="No verifiable national survey available yet.",
    )
    assert item.value is None
    assert item.evidence_status == "unknown"


def test_missing_unit_fails_for_numerical_evidence() -> None:
    """TEST 5: Missing unit fails when a numerical value is provided."""
    with pytest.raises(ValidationError) as exc:
        EvidenceItem(
            metric="Market size",
            value=1000000.0,
            unit=None,  # Missing unit
            source_name="Test Source",
            evidence_status=EvidenceStatus.VERIFIED,
        )
    assert "unit" in str(exc.value).lower()


def test_geography_preserved() -> None:
    """TEST 6: Geography field is explicitly preserved and whitespace sanitized."""
    item = EvidenceItem(
        metric="Urban households in Chennai",
        value=2500000.0,
        unit="households",
        geography="  Chennai  ",
        source_name="Municipal Corporation of Chennai",
        evidence_status=EvidenceStatus.VERIFIED,
    )
    assert item.geography == "Chennai"


def test_year_preserved_and_bounds_validated() -> None:
    """TEST 7: Year is preserved and invalid years out of range are rejected."""
    # Valid year
    item = EvidenceItem(
        metric="Active internet users",
        value=800000000.0,
        unit="users",
        geography="India",
        year=2024,
        source_name="Telecom Regulatory Authority",
        evidence_status=EvidenceStatus.VERIFIED,
    )
    assert item.year == 2024

    # Invalid year (out of bounds)
    with pytest.raises(ValidationError):
        EvidenceItem(
            metric="Active internet users",
            value=800000000.0,
            unit="users",
            year=1850,
            source_name="Test",
            evidence_status=EvidenceStatus.VERIFIED,
        )


# ---------------------------------------------------------------------------
# Service Domain Operations Tests
# ---------------------------------------------------------------------------

def test_service_normalize_evidence_item() -> None:
    """EvidenceService properly normalizes assumed source_type default."""
    item = EvidenceItem(
        metric="Adoption rate assumption",
        value=0.02,
        unit="%",
        evidence_status=EvidenceStatus.ASSUMED,
        source_type=SourceType.UNKNOWN,
    )
    normalized = evidence_service.normalize_evidence_item(item)
    assert normalized.source_type == SourceType.ASSUMPTION.value


def test_service_inspect_evidence_quality() -> None:
    """EvidenceService quality inspection identifies caveats and warnings."""
    item = EvidenceItem(
        metric="Historical developer count",
        value=1500000.0,
        unit="developers",
        geography="India",
        year=2018,  # Historical year < 2020
        source_name="Industry Survey 2018",
        evidence_status=EvidenceStatus.VERIFIED,
    )
    inspection = evidence_service.inspect_evidence_quality(item)
    assert inspection["is_verified"] is True
    assert any("2018" in w for w in inspection["warnings"])
    assert any("source_url" in w for w in inspection["warnings"])


def test_service_to_domain_record() -> None:
    """Conversion from schema EvidenceItem to domain EvidenceRecord."""
    item = EvidenceItem(
        metric="Number of registered MSMEs",
        value=63000000.0,
        unit="enterprises",
        geography="India",
        year=2024,
        source_name="Ministry of MSME",
        source_url="https://example.gov.in/msme-stats",
        source_type=SourceType.GOVERNMENT,
        confidence=ConfidenceLevel.HIGH,
        evidence_status=EvidenceStatus.VERIFIED,
    )
    record = evidence_service.to_domain_record(item)
    assert isinstance(record, EvidenceRecord)
    assert record.metric == "Number of registered MSMEs"
    assert record.value == 63000000.0
    assert record.unit == "enterprises"
    assert record.source_type == SourceType.GOVERNMENT
    assert record.confidence == ConfidenceLevel.HIGH


# ---------------------------------------------------------------------------
# API Endpoint Tests (POST /api/v1/evidence/validate)
# ---------------------------------------------------------------------------

def test_api_validate_evidence_success() -> None:
    """API endpoint returns 200 for valid verified evidence item."""
    payload = {
        "metric": "Number of college students in India",
        "value": 43000000.0,
        "unit": "students",
        "geography": "India",
        "year": 2025,
        "source_name": "Ministry of Education / AISHE",
        "source_url": "https://example.gov.in/aishe-report",
        "source_type": "official_statistics",
        "confidence": "high",
        "evidence_status": "verified",
        "used_for": "TAM population sizing",
    }
    response = client.post("/api/v1/evidence/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["metric"] == "Number of college students in India"
    assert data["value"] == 43000000.0
    assert data["unit"] == "students"
    assert data["geography"] == "India"
    assert data["year"] == 2025
    assert data["source_name"] == "Ministry of Education / AISHE"
    assert data["evidence_status"] == "verified"


def test_api_validate_evidence_rejected_missing_source() -> None:
    """API endpoint returns 422 when verified evidence lacks a source."""
    payload = {
        "metric": "Number of college students in India",
        "value": 43000000.0,
        "unit": "students",
        "geography": "India",
        "evidence_status": "verified",
        # Missing source_name
    }
    response = client.post("/api/v1/evidence/validate", json=payload)
    assert response.status_code == 422


def test_api_validate_evidence_rejected_missing_unit() -> None:
    """API endpoint returns 422 when numerical value lacks a unit."""
    payload = {
        "metric": "Market revenue",
        "value": 5000000.0,
        # Missing unit
        "source_name": "Test Source",
        "evidence_status": "verified",
    }
    response = client.post("/api/v1/evidence/validate", json=payload)
    assert response.status_code == 422


def test_api_validate_evidence_rejected_unknown_with_value() -> None:
    """API endpoint returns 422 when unknown evidence contains a numerical value."""
    payload = {
        "metric": "Unmeasured market segment",
        "value": 12345.0,  # Invalid for unknown
        "unit": "USD",
        "evidence_status": "unknown",
    }
    response = client.post("/api/v1/evidence/validate", json=payload)
    assert response.status_code == 422
