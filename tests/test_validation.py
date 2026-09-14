import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.discovery import DiscoveryLifecycleStage
from app.schemas.extraction import (
    ExtractedEvidenceCandidate,
    ExtractionMethod,
)
from app.schemas.evidence import ConfidenceLevel
from app.schemas.validation import (
    EvidenceConfidence,
    EvidenceValidationResult,
    EvidenceValidationStatus,
    TriangulationRequest,
    TriangulationResult,
)
from app.services.validation_service import EvidenceValidationService

client = TestClient(app)
validation_service = EvidenceValidationService()


# ---------------------------------------------------------------------------
# Unit Tests: Structural Candidate Validation
# ---------------------------------------------------------------------------

def test_1_valid_candidate_passes_validation() -> None:
    """TEST 1: A well-formed candidate passes structural validation and moves to VALIDATED stage."""
    candidate = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        raw_value_expression="43 million",
        unit="students",
        geography="India",
        year=2025,
        source_name="Ministry of Education / AISHE",
        source_url="https://statistics.gov.in/aishe-2025",
        source_context="According to the AISHE survey, there are 43 million college students enrolled in India in 2025.",
        extraction_method=ExtractionMethod.DETERMINISTIC_PATTERN,
        extraction_confidence=ConfidenceLevel.HIGH,
    )

    result = validation_service.validate_candidate(candidate)

    assert result.is_valid is True
    assert result.validation_status == EvidenceValidationStatus.VALID
    assert result.lifecycle_stage == DiscoveryLifecycleStage.VALIDATED
    assert result.value == 43000000.0
    assert result.unit == "students"
    assert result.geography == "India"
    assert result.year == 2025
    assert result.source_quality_score >= 0.90
    assert result.corroborating_source_count == 1
    assert result.conflicting_source_count == 0


def test_2_missing_value_rejected() -> None:
    """TEST 2: Discrete candidate without a numerical value is rejected as INVALID."""
    candidate = ExtractedEvidenceCandidate(
        metric="college students",
        value=None,
        unit="students",
        geography="India",
        source_url="https://statistics.gov.in/aishe",
        source_context="College students in India.",
    )

    result = validation_service.validate_candidate(candidate)

    assert result.is_valid is False
    assert result.validation_status == EvidenceValidationStatus.INVALID
    assert any("Missing required numerical value" in r for r in result.validation_reasons)


def test_3_invalid_negative_value_rejected() -> None:
    """TEST 3: Negative numerical values for count/population metrics are rejected."""
    candidate = ExtractedEvidenceCandidate(
        metric="college students",
        value=-500000.0,
        unit="students",
        geography="India",
        source_url="https://statistics.gov.in/aishe",
        source_context="Negative 500k college students enrolled.",
    )

    result = validation_service.validate_candidate(candidate)

    assert result.is_valid is False
    assert result.validation_status == EvidenceValidationStatus.INVALID
    assert any("Negative value" in r for r in result.validation_reasons)


def test_4_invalid_range_rejected() -> None:
    """TEST 4: Range candidate with range_min > range_max is rejected."""
    candidate = ExtractedEvidenceCandidate(
        metric="market size",
        value=None,
        unit="USD",
        is_range_or_approximate=True,
        range_min=15000000.0,
        range_max=10000000.0,  # Invalid: min > max
        source_url="https://research.example.org/edtech",
        source_context="The market is between 15M and 10M USD.",
    )

    result = validation_service.validate_candidate(candidate)

    assert result.is_valid is False
    assert result.validation_status == EvidenceValidationStatus.INVALID
    assert any("range_min" in r and "range_max" in r for r in result.validation_reasons)


def test_5_invalid_year_rejected() -> None:
    """TEST 5: Impossible reference years outside 1900-2100 are rejected."""
    with pytest.raises(ValidationError):
        ExtractedEvidenceCandidate(
            metric="college students",
            value=43000000.0,
            unit="students",
            year=1820,  # Unrealistic year
            source_url="https://statistics.gov.in/aishe",
            source_context="Census in 1820.",
        )


def test_6_missing_source_url_rejected() -> None:
    """TEST 6: Candidate lacking a valid source URL is rejected."""
    with pytest.raises(ValidationError):
        ExtractedEvidenceCandidate(
            metric="college students",
            value=43000000.0,
            unit="students",
            source_url="",  # Empty URL
            source_context="Reported 43 million students.",
        )


def test_7_missing_source_context_rejected() -> None:
    """TEST 7: Candidate lacking source context is rejected for traceability failure."""
    with pytest.raises(ValidationError):
        ExtractedEvidenceCandidate(
            metric="college students",
            value=43000000.0,
            unit="students",
            source_url="https://statistics.gov.in/aishe",
            source_context="",  # Missing context
        )


# ---------------------------------------------------------------------------
# Unit Tests: Deduplication & Conflict Detection
# ---------------------------------------------------------------------------

def test_8_duplicate_candidates_detected() -> None:
    """TEST 8: Identical candidate claims are clustered into a DeduplicationGroup."""
    cand1 = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        unit="students",
        geography="India",
        year=2025,
        source_url="https://statistics.gov.in/aishe-1",
        source_context="43 million college students in 2025.",
    )
    cand2 = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        unit="students",
        geography="India",
        year=2025,
        source_url="https://education.gov.in/aishe-2",
        source_context="India has 43 million college students in 2025.",
    )

    groups = validation_service.deduplicate_candidates([cand1, cand2])

    assert len(groups) == 1
    assert groups[0].canonical_value == 43000000.0
    assert len(groups[0].candidates) == 2
    assert len(groups[0].distinct_domains) == 2


def test_9_normalized_values_detected_as_duplicates() -> None:
    """TEST 9: Candidates with differing surface syntax normalize into identical deduplication groups."""
    cand1 = ExtractedEvidenceCandidate(
        metric="Number of college students",
        value=43000000.0,
        raw_value_expression="43 million",
        unit="students",
        geography="India",
        year=2025,
        source_url="https://statistics.gov.in/rep1",
        source_context="Total number of college students is 43 million.",
    )
    cand2 = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        raw_value_expression="43,000,000",
        unit="student",
        geography="India",
        year=2025,
        source_url="https://education.gov.in/rep2",
        source_context="43,000,000 student enrollment.",
    )

    groups = validation_service.deduplicate_candidates([cand1, cand2])

    assert len(groups) == 1
    assert groups[0].canonical_value == 43000000.0
    assert len(groups[0].candidates) == 2


def test_10_different_values_are_not_deduplicated() -> None:
    """TEST 10: Candidates with different values for the same metric are preserved as separate groups."""
    cand1 = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        unit="students",
        geography="India",
        year=2025,
        source_url="https://statistics.gov.in/rep1",
        source_context="43 million college students.",
    )
    cand2 = ExtractedEvidenceCandidate(
        metric="college students",
        value=47000000.0,  # Materially different value
        unit="students",
        geography="India",
        year=2025,
        source_url="https://analytics.example.com/rep2",
        source_context="47 million college students.",
    )

    groups = validation_service.deduplicate_candidates([cand1, cand2])

    assert len(groups) == 2


def test_11_conflicting_sources_detected() -> None:
    """TEST 11: Materially contradictory claims across sources are detected and grouped as CONFLICT."""
    cand1 = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        unit="students",
        geography="India",
        year=2025,
        source_url="https://statistics.gov.in/rep1",
        source_context="43 million college students in 2025.",
    )
    cand2 = ExtractedEvidenceCandidate(
        metric="college students",
        value=41000000.0,
        unit="students",
        geography="India",
        year=2025,
        source_url="https://research.example.org/rep2",
        source_context="41 million college students in 2025.",
    )

    dup_groups = validation_service.deduplicate_candidates([cand1, cand2])
    conflicts = validation_service.detect_conflicts(dup_groups)

    assert len(conflicts) == 1
    assert set(conflicts[0].conflicting_values) == {43000000.0, 41000000.0}
    assert "Conflicting values" in conflicts[0].reason


# ---------------------------------------------------------------------------
# Unit Tests: Multi-Source Triangulation Rules
# ---------------------------------------------------------------------------

def test_12_same_url_is_not_counted_twice_for_corroboration() -> None:
    """TEST 12: Repeated submissions of the same URL or domain count as 1 independent source and stay VALIDATED."""
    cand1 = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        unit="students",
        geography="India",
        year=2025,
        source_url="https://statistics.gov.in/aishe",
        source_context="43 million college students in Section 1.",
    )
    cand2 = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        unit="students",
        geography="India",
        year=2025,
        source_url="https://statistics.gov.in/aishe",  # Same exact URL
        source_context="43 million college students in Section 2.",
    )

    result = validation_service.triangulate_evidence([cand1, cand2])

    assert result.total_candidates_processed == 2
    assert len(result.verified_items) == 0  # NOT verified!
    assert len(result.validated_items) == 1
    assert result.validated_items[0].corroborating_source_count == 1
    assert result.validated_items[0].lifecycle_stage == DiscoveryLifecycleStage.VALIDATED


def test_13_two_independent_matching_sources_become_verified() -> None:
    """TEST 13: Two distinct independent domain sources agreeing on a metric elevate it to VERIFIED."""
    cand1 = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        unit="students",
        geography="India",
        year=2025,
        source_name="Ministry of Education",
        source_url="https://statistics.gov.in/report-1",
        source_context="43 million college students enrolled in India in 2025.",
    )
    cand2 = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        unit="students",
        geography="India",
        year=2025,
        source_name="Higher Education Commission",
        source_url="https://education.gov.in/report-2",  # Distinct domain
        source_context="India has 43 million students in colleges in 2025.",
    )

    result = validation_service.triangulate_evidence([cand1, cand2])

    assert len(result.verified_items) == 1
    item = result.verified_items[0]
    assert item.lifecycle_stage == DiscoveryLifecycleStage.VERIFIED
    assert item.corroborating_source_count == 2
    assert item.confidence in (EvidenceConfidence.HIGH, EvidenceConfidence.VERY_HIGH)
    assert len(item.corroborating_sources) == 2


def test_14_one_source_does_not_automatically_become_verified() -> None:
    """TEST 14: A single valid source must remain VALIDATED and cannot become VERIFIED."""
    candidate = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        unit="students",
        geography="India",
        year=2025,
        source_url="https://statistics.gov.in/single-source",
        source_context="43 million college students in 2025.",
    )

    result = validation_service.triangulate_evidence([candidate])

    assert len(result.verified_items) == 0
    assert len(result.validated_items) == 1
    assert result.validated_items[0].lifecycle_stage == DiscoveryLifecycleStage.VALIDATED
    assert result.validated_items[0].confidence == EvidenceConfidence.MEDIUM


def test_15_high_quality_independent_sources_increase_confidence() -> None:
    """TEST 15: Two independent government statistical sources achieve VERY_HIGH confidence."""
    cand1 = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        raw_value_expression="43 million",
        unit="students",
        geography="India",
        year=2025,
        source_name="National Statistical Office",
        source_url="https://mospi.gov.in/nso-report",
        source_context="NSO records 43 million students in 2025.",
    )
    cand2 = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        raw_value_expression="43 million",
        unit="students",
        geography="India",
        year=2025,
        source_name="Ministry of Education",
        source_url="https://education.gov.in/he-report",
        source_context="Education census confirms 43 million students in 2025.",
    )

    result = validation_service.triangulate_evidence([cand1, cand2])

    assert len(result.verified_items) == 1
    assert result.verified_items[0].confidence == EvidenceConfidence.VERY_HIGH


def test_16_conflict_prevents_very_high_confidence() -> None:
    """TEST 16: An active conflict prevents any candidate from attaining VERY_HIGH confidence and flags CONFLICT status."""
    cand1 = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        unit="students",
        geography="India",
        year=2025,
        source_url="https://statistics.gov.in/rep1",
        source_context="43 million college students.",
    )
    cand2 = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        unit="students",
        geography="India",
        year=2025,
        source_url="https://education.gov.in/rep2",
        source_context="43 million college students.",
    )
    cand3 = ExtractedEvidenceCandidate(
        metric="college students",
        value=41000000.0,  # Discrepancy
        unit="students",
        geography="India",
        year=2025,
        source_url="https://research.example.org/rep3",
        source_context="41 million college students.",
    )

    result = validation_service.triangulate_evidence([cand1, cand2, cand3])

    assert len(result.conflict_groups) == 1
    # Check all validated items
    for item in result.validated_items:
        assert item.validation_status == EvidenceValidationStatus.CONFLICT
        assert item.confidence != EvidenceConfidence.VERY_HIGH
        assert item.lifecycle_stage == DiscoveryLifecycleStage.VALIDATED


def test_17_lifecycle_cannot_jump_directly_to_verified() -> None:
    """TEST 17: ExtractedEvidenceCandidate schema validator forbids lifecycle_stage='verified'."""
    with pytest.raises(ValidationError):
        ExtractedEvidenceCandidate(
            metric="college students",
            value=43000000.0,
            unit="students",
            source_url="https://statistics.gov.in/report",
            source_context="43 million students.",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,  # Invalid jump
        )


def test_18_provenance_is_preserved_after_deduplication() -> None:
    """TEST 18: Complete source URLs, names, snippets, and quality scores are preserved in corroborating_sources."""
    cand1 = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        unit="students",
        geography="India",
        year=2025,
        source_name="Gov Statistics Bureau",
        source_url="https://statistics.gov.in/rep1",
        source_context="Snippet from Gov Stats Bureau 1.",
    )
    cand2 = ExtractedEvidenceCandidate(
        metric="college students",
        value=43000000.0,
        unit="students",
        geography="India",
        year=2025,
        source_name="Edu Ministry",
        source_url="https://education.gov.in/rep2",
        source_context="Snippet from Edu Ministry 2.",
    )

    result = validation_service.triangulate_evidence([cand1, cand2])

    assert len(result.verified_items) == 1
    v_item = result.verified_items[0]
    assert len(v_item.corroborating_sources) == 2
    urls = [s.source_url for s in v_item.corroborating_sources]
    assert "https://statistics.gov.in/rep1" in urls
    assert "https://education.gov.in/rep2" in urls
    names = [s.source_name for s in v_item.corroborating_sources]
    assert "Gov Statistics Bureau" in names
    assert "Edu Ministry" in names


# ---------------------------------------------------------------------------
# API Endpoint Integration Tests
# ---------------------------------------------------------------------------

def test_19_api_validation_endpoint_works() -> None:
    """TEST 19: POST /api/v1/evidence/validate successfully validates an ExtractedEvidenceCandidate."""
    payload = {
        "metric": "college students",
        "value": 43000000.0,
        "raw_value_expression": "43 million",
        "unit": "students",
        "geography": "India",
        "year": 2025,
        "source_name": "Ministry of Education",
        "source_url": "https://statistics.gov.in/aishe",
        "source_context": "India has 43 million college students in 2025.",
    }

    response = client.post("/api/v1/evidence/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["metric"] == "college students"
    assert data["value"] == 43000000.0
    assert data["validation_status"] == "valid"
    assert data["lifecycle_stage"] == "validated"
    assert data["source_quality_score"] >= 0.90


def test_20_api_triangulation_and_required_manual_case() -> None:
    """TEST 20: POST /api/v1/evidence/triangulate with the exact 3-source manual case from requirements:

    Source 1: statistics.gov.in (43M, India, 2025)
    Source 2: education.gov.in (43M, India, 2025)
    Source 3: research.example.org (41M, India, 2025)
    """
    payload = {
        "candidates": [
            {
                "metric": "college students",
                "value": 43000000.0,
                "unit": "students",
                "geography": "India",
                "year": 2025,
                "source_name": "Government Statistics Source",
                "source_url": "https://statistics.gov.in/example-1",
                "source_context": "Government statistics report 43 million college students in 2025.",
            },
            {
                "metric": "college students",
                "value": 43000000.0,
                "unit": "students",
                "geography": "India",
                "year": 2025,
                "source_name": "Education Statistics Source",
                "source_url": "https://education.gov.in/example-2",
                "source_context": "Education department confirms 43 million college students in 2025.",
            },
            {
                "metric": "college students",
                "value": 41000000.0,
                "unit": "students",
                "geography": "India",
                "year": 2025,
                "source_name": "Research Source",
                "source_url": "https://research.example.org/example-3",
                "source_context": "Independent research finds 41 million college students in 2025.",
            },
        ]
    }

    response = client.post("/api/v1/evidence/triangulate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["total_candidates_processed"] == 3
    # Conflict group detected
    assert len(data["conflict_groups"]) == 1
    conflict = data["conflict_groups"][0]
    assert set(conflict["conflicting_values"]) == {43000000.0, 41000000.0}
    assert "Conflicting values reported by independent sources" in conflict["reason"]

    # All candidates preserved in validated_items
    assert len(data["validated_items"]) == 2  # Two unique claim groups: 43M and 41M
    for item in data["validated_items"]:
        assert item["validation_status"] == "conflict"
        assert item["conflicting_source_count"] >= 1
        assert len(item["conflicting_sources"]) >= 1

    # Source 1 & 2 grouped together in corroborating sources for 43M claim
    item_43m = next(item for item in data["validated_items"] if item["value"] == 43000000.0)
    assert item_43m["corroborating_source_count"] == 2
    corrob_urls = [s["source_url"] for s in item_43m["corroborating_sources"]]
    assert "https://statistics.gov.in/example-1" in corrob_urls
    assert "https://education.gov.in/example-2" in corrob_urls

    # Source 3 explicitly listed as conflicting source
    conflict_urls = [s["source_url"] for s in item_43m["conflicting_sources"]]
    assert "https://research.example.org/example-3" in conflict_urls


def test_validation_rejects_noise_and_unrecognized_units() -> None:
    """Validation rejects candidates with non-market units such as Birds, Distributions, Tips, LTS."""
    service = EvidenceValidationService()

    invalid_candidates = [
        ExtractedEvidenceCandidate(
            metric="Birds",
            value=2026.0,
            unit="Birds",
            source_url="https://example.com/nature",
            source_context="We counted 2,026 Birds in the annual survey.",
        ),
        ExtractedEvidenceCandidate(
            metric="Best Linux Distributions",
            value=16.0,
            unit="Distributions",
            source_url="https://example.com/tech",
            source_context="16 Best Linux Distributions for developers.",
        ),
        ExtractedEvidenceCandidate(
            metric="Simple Tips",
            value=10.0,
            unit="Tips",
            source_url="https://example.com/tips",
            source_context="10 Simple Tips to improve code.",
        ),
        ExtractedEvidenceCandidate(
            metric="LTS",
            value=24.04,
            unit="LTS",
            source_url="https://example.com/os",
            source_context="Version 24.04 LTS released.",
        ),
    ]

    for cand in invalid_candidates:
        result = service.validate_candidate(cand)
        assert result.is_valid is False
        assert result.validation_status == EvidenceValidationStatus.INVALID
        assert result.lifecycle_stage == DiscoveryLifecycleStage.EXTRACTED


def test_rejects_generic_metric_word_without_real_metric_type() -> None:
    """Validation rejects generic 'metric' word without recognized market metric type."""
    service = EvidenceValidationService()
    cand = ExtractedEvidenceCandidate(
        metric="metric",
        value=50000.0,
        unit="metric",
        source_url="https://example.com/generic",
        source_context="The metric was calculated as 50000.",
    )
    result = service.validate_candidate(cand)
    assert result.is_valid is False
    assert result.validation_status == EvidenceValidationStatus.INVALID


