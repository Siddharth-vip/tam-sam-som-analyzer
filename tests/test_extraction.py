import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.fetching.models import FetchedSource, FetchStatus
from app.main import app
from app.schemas.discovery import DiscoveryLifecycleStage
from app.schemas.extraction import (
    ExtractedEvidenceCandidate,
    ExtractionMethod,
    ExtractionRequest,
    ExtractionResponse,
    ExtractionStatus,
)
from app.services.extraction_service import EvidenceExtractionService

client = TestClient(app)
extractor = EvidenceExtractionService()


# ---------------------------------------------------------------------------
# Deterministic Pattern Extraction Unit Tests
# ---------------------------------------------------------------------------

def test_extract_exact_count_and_geography() -> None:
    """TEST 13, 14, 15: 'India has 43 million college students' -> 43,000,000, students, India, year=null."""
    sentence = "India has 43 million college students enrolled in universities across the country."
    candidates = extractor.extract_candidates_from_sentence(
        sentence=sentence,
        source_url="https://example.gov.in/report",
        source_name="Ministry of Education",
    )
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.value == 43000000.0
    assert cand.unit == "students"
    assert cand.geography == "India"
    assert cand.year is None  # TEST 17: Missing year remains null (never invented)
    assert cand.source_url == "https://example.gov.in/report"
    assert "43 million college students" in cand.source_context
    assert cand.lifecycle_stage == DiscoveryLifecycleStage.EXTRACTED.value


def test_extract_currency_and_explicit_year() -> None:
    """TEST 13, 16: 'The market was valued at USD 2.5 billion in 2024' -> 2,500,000,000, USD, year=2024."""
    sentence = "The market was valued at USD 2.5 billion in 2024 with substantial growth projected."
    candidates = extractor.extract_candidates_from_sentence(
        sentence=sentence,
        source_url="https://market-research.org/report",
        source_name="Market Research Org",
    )
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.value == 2500000000.0
    assert cand.unit == "USD"
    assert cand.year == 2024
    assert cand.source_context == sentence


def test_extract_range_preserves_bounds_without_arbitrary_point() -> None:
    """TEST 18: '10–15 million developers in Asia' preserves interval bounds; scalar value is None."""
    sentence = "There are 10–15 million developers in Asia contributing to open-source software."
    candidates = extractor.extract_candidates_from_sentence(
        sentence=sentence,
        source_url="https://developer-survey.com/asia",
    )
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.is_range_or_approximate is True
    assert cand.value is None  # Value must NOT be arbitrarily picked
    assert cand.range_min == 10000000.0
    assert cand.range_max == 15000000.0
    assert cand.geography == "Asia"


def test_extract_approximate_qualifier_preserves_context() -> None:
    """TEST 19: 'more than 10 million users' preserves approximate qualifier; scalar value is None."""
    sentence = "The platform has attracted more than 10 million users across major metro areas."
    candidates = extractor.extract_candidates_from_sentence(
        sentence=sentence,
        source_url="https://example.com/growth",
    )
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.is_range_or_approximate is True
    assert cand.value is None  # Value not rounded to exact 10M
    assert "more than 10 million" in cand.raw_value_expression.lower()
    assert cand.source_context == sentence


def test_missing_numerical_value_returns_no_candidates() -> None:
    """TEST 20: Descriptive text without numerical statements produces NO_METRICS_FOUND."""
    fetched = FetchedSource(
        original_url="https://example.com/about",
        title="About Us",
        content="We provide online learning tools for students and professionals across the world.",
        fetch_status=FetchStatus.SUCCESS,
    )
    request = ExtractionRequest(source=fetched)
    response = extractor.extract_evidence_from_source(request)

    assert response.status == ExtractionStatus.NO_METRICS_FOUND
    assert response.total_candidates_found == 0
    assert response.candidates == []


def test_extracted_candidate_cannot_claim_verified_stage() -> None:
    """TEST 24: Epistemic guard ensures ExtractedEvidenceCandidate cannot have lifecycle_stage='verified'."""
    with pytest.raises(ValidationError) as exc:
        ExtractedEvidenceCandidate(
            metric="college students",
            value=43000000.0,
            unit="students",
            source_url="https://example.com",
            source_context="Context",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        )
    assert "verified" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# API Endpoint Tests (POST /api/v1/evidence/extract)
# ---------------------------------------------------------------------------

def test_api_extract_evidence_success() -> None:
    """TEST 25: API endpoint returns 200 with extracted candidates from FetchedSource."""
    payload = {
        "source": {
            "original_url": "https://statistics.gov.in/report",
            "title": "National Survey",
            "content": "India has 43 million college students in 2025. The market was worth USD 500 million.",
            "fetch_status": "success",
            "lifecycle_stage": "fetched",
            "source_name": "National Statistics Commission",
        }
    }
    response = client.post("/api/v1/evidence/extract", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_candidates_found"] >= 1
    assert data["lifecycle_stage"] == "extracted"

    # Verify first candidate structure
    c0 = data["candidates"][0]
    assert c0["source_url"] == "https://statistics.gov.in/report"
    assert c0["lifecycle_stage"] == "extracted"
    assert "students" in c0["unit"] or "USD" in c0["unit"]


def test_extraction_rejects_listicles_and_non_market_noise() -> None:
    """Regression test: Listicle headers, software distros, birds, and random numbers are rejected."""
    noise_sentences = [
        "We spotted 2,026 Birds in the annual migratory survey across national parks.",
        "Here are 16 Best Linux Distributions to try on your modern workstation.",
        "Check out these 14 Top Outstanding Open Source LLMs for NLP workloads.",
        "Ubuntu released version 24.04 LTS with extended long-term support.",
        "10 Simple Tips to optimize your cloud architecture efficiently.",
        "Only 1 Tired developer stayed up all night debugging the deployment.",
    ]

    for sentence in noise_sentences:
        candidates = extractor.extract_candidates_from_sentence(
            sentence=sentence,
            source_url="https://example.com/blog",
        )
        assert len(candidates) == 0, f"Expected 0 candidates for noise sentence: '{sentence}', got: {candidates}"

    # Verify full source document containing only noise returns NO_METRICS_FOUND
    noise_doc = FetchedSource(
        original_url="https://ubercloud.com.au/tech-news",
        title="UBERCLOUD - Leading Technology News",
        content="We counted 2,026 Birds in nature. Here are 16 Best Linux Distributions and 14 LLMs with Ubuntu 24.04 LTS and 10 Simple Tips for 1 Tired engineer.",
        fetch_status=FetchStatus.SUCCESS,
    )
    resp = extractor.extract_evidence_from_source(ExtractionRequest(source=noise_doc))
    assert resp.status == ExtractionStatus.NO_METRICS_FOUND
    assert len(resp.candidates) == 0
    assert resp.total_candidates_found == 0

