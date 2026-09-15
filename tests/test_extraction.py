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
    MarketMetricType,
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


def test_regression_requirement_12_semantic_metric_distinction_and_jump_from():
    """Regression tests for requirement 12 A-G:
    A. 'jump from 128 million to 150 million'
    B. 'increased from 128 to 150 million users'
    C. 'market grew 12.8%'
    D. 'CAGR of 12.8%'
    E. 'market share of 28%'
    F. '$128 million market size'
    G. Source containing multiple metrics where one malformed metric exists.
    """
    # A. "jump from 128 million to 150 million"
    s_a = "The transaction volume witnessed a jump from 128 million to 150 million in 2025."
    cands_a = extractor.extract_candidates_from_sentence(s_a, "https://report.com/a")
    assert len(cands_a) >= 1
    assert cands_a[0].is_range_or_approximate is True
    assert cands_a[0].range_min == 128_000_000.0
    assert cands_a[0].range_max == 150_000_000.0
    assert cands_a[0].unit != "%"
    assert cands_a[0].value != 128.0

    # B. "increased from 128 to 150 million users"
    s_b = "The mobile application increased from 128 to 150 million users across India."
    cands_b = extractor.extract_candidates_from_sentence(s_b, "https://report.com/b")
    assert len(cands_b) >= 1
    assert cands_b[0].is_range_or_approximate is True
    assert cands_b[0].range_min == 128_000_000.0
    assert cands_b[0].range_max == 150_000_000.0
    assert cands_b[0].unit == "users"
    assert cands_b[0].value != 128.0

    # C. "market grew 12.8%"
    s_c = "The sustainable fashion market grew 12.8% year over year."
    cands_c = extractor.extract_candidates_from_sentence(s_c, "https://report.com/c")
    assert len(cands_c) >= 1
    assert cands_c[0].value == 12.8
    assert cands_c[0].unit == "%"
    assert cands_c[0].metric_type == MarketMetricType.GROWTH_RATE

    # D. "CAGR of 12.8%"
    s_d = "The industry is projected to expand at a CAGR of 12.8% through 2030."
    cands_d = extractor.extract_candidates_from_sentence(s_d, "https://report.com/d")
    assert len(cands_d) >= 1
    assert cands_d[0].value == 12.8
    assert cands_d[0].unit == "%"
    assert cands_d[0].metric_type in (MarketMetricType.GROWTH_RATE, MarketMetricType.CAGR)

    # E. "market share of 28%"
    s_e = "The top marketplace commands a market share of 28% in urban regions."
    cands_e = extractor.extract_candidates_from_sentence(s_e, "https://report.com/e")
    assert len(cands_e) >= 1
    assert cands_e[0].value == 28.0
    assert cands_e[0].unit == "%"
    assert cands_e[0].metric_type == MarketMetricType.MARKET_SHARE

    # F. "$128 million market size"
    s_f = "The sustainable apparel sector reached a $128 million market size in India in 2025."
    cands_f = extractor.extract_candidates_from_sentence(s_f, "https://report.com/f")
    assert len(cands_f) >= 1
    market_cands = [c for c in cands_f if c.unit == "USD"]
    assert len(market_cands) >= 1
    assert market_cands[0].value == 128_000_000.0
    assert market_cands[0].geography == "India"
    assert market_cands[0].year == 2025

    # G. Source containing multiple metrics where one malformed metric exists.
    # The malformed candidate must NOT crash candidate extraction or triangulation.
    content_g = """
    The sustainable apparel market size in India was USD 128 million in 2025.
    Customer adoption saw a jump from 128 to 150 million users across the country.
    E-commerce penetration is at 28% of total apparel sales.
    The sector grew 12.8% year on year.
    """
    source_g = FetchedSource(
        original_url="https://apparel-insights.com/report",
        title="India Sustainable Apparel Report 2025",
        content=content_g,
        fetch_status=FetchStatus.SUCCESS,
    )
    resp_g = extractor.extract_evidence_from_source(ExtractionRequest(source=source_g))
    assert resp_g.status == ExtractionStatus.SUCCESS
    assert resp_g.total_candidates_found >= 3
    # Ensure all extracted candidates have valid units and reasonable values
    for cand in resp_g.candidates:
        if cand.unit == "%":
            assert cand.value is not None and 0.0 <= cand.value <= 100.0
        elif cand.is_range_or_approximate:
            assert cand.range_min is not None and cand.range_max is not None
            assert cand.range_min <= cand.range_max


