import json
import os
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.fetching.models import FetchedSource, FetchStatus
from app.fetching.security import is_safe_url, validate_url_safety, InsecureUrlException
from app.discovery.live_provider import infer_source_category, calculate_domain_authority_score
from app.schemas.business import BusinessAnalysis, CompetitorInfo
from app.schemas.discovery import SourceCategory, DiscoveredSource, DiscoveryLifecycleStage
from app.schemas.extraction import ExtractedEvidenceCandidate
from app.schemas.pipeline import PipelineRequest, PipelineResult, PipelineStatus
from app.services.extraction_service import EvidenceExtractionService
from app.storage.database import get_db_connection, init_db
from app.storage.repository import AnalysisRepository


client = TestClient(app)


# ===========================================================================
# 1. SECURITY & SSRF PROTECTION TESTS
# ===========================================================================

def test_ssrf_blocks_loopback_and_private_addresses():
    """Verify that loopback, private ranges, and link-local are rejected."""
    assert not is_safe_url("http://127.0.0.1:8000/api")
    assert not is_safe_url("http://localhost:3000")
    assert not is_safe_url("http://192.168.1.1/admin")
    assert not is_safe_url("http://10.0.0.1/status")
    assert not is_safe_url("http://172.16.0.1/data")
    assert not is_safe_url("http://0.0.0.0:80")


def test_ssrf_blocks_cloud_metadata_endpoints():
    """Verify that AWS/GCP/Azure cloud metadata endpoints are strictly blocked."""
    assert not is_safe_url("http://169.254.169.254/latest/meta-data/")
    assert not is_safe_url("http://metadata.google.internal/computeMetadata/v1/")
    assert not is_safe_url("http://metadata.azure.com/metadata/instance")
    assert not is_safe_url("http://instance-data/latest/meta-data/")


def test_ssrf_blocks_ipv6_loopback_and_mapped_addresses():
    """Verify IPv6 loopbacks and IPv4-mapped IPv6 are blocked."""
    assert not is_safe_url("http://[::1]/")
    assert not is_safe_url("http://[::ffff:127.0.0.1]/")


def test_ssrf_blocks_obfuscated_ip_formats():
    """Verify decimal and hex representation of loopback/private IPs are blocked."""
    assert not is_safe_url("http://2130706433/")  # 127.0.0.1 in decimal
    assert not is_safe_url("http://0x7f000001/")  # 127.0.0.1 in hex


def test_ssrf_blocks_non_standard_sensitive_ports():
    """Verify non-web ports (e.g. database, SSH, Ollama) are blocked."""
    assert not is_safe_url("http://example.com:22/ssh")
    assert not is_safe_url("http://example.com:3306/mysql")
    assert not is_safe_url("http://example.com:5432/postgres")
    assert not is_safe_url("http://example.com:11434/api/generate")
    assert not is_safe_url("http://example.com:6379/redis")


def test_ssrf_allows_valid_public_web_urls():
    """Verify legitimate public web URLs on standard ports are allowed."""
    assert is_safe_url("https://www.statista.com/outlook/edtech")
    assert is_safe_url("https://data.gov.in/dataset/education-statistics")
    assert is_safe_url("http://example.org/report.html")
    assert is_safe_url("https://example.com:8443/data")
    assert is_safe_url("http://example.com:8080/data")


def test_validate_url_safety_raises_exception():
    """Verify validate_url_safety raises InsecureUrlException for blocked URLs."""
    with pytest.raises(InsecureUrlException):
        validate_url_safety("http://127.0.0.1:8000/internal")


# ===========================================================================
# 2. EVIDENCE QUALITY & DOMAIN SCORING TESTS
# ===========================================================================

def test_domain_categorization_and_authority_scoring():
    """Verify institutional domains are categorized and scored accurately."""
    # Government
    cat_gov = infer_source_category("data.gov.in")
    assert cat_gov == SourceCategory.OFFICIAL_GOVERNMENT
    assert calculate_domain_authority_score("data.gov.in", cat_gov) >= 0.90

    cat_worldbank = infer_source_category("worldbank.org")
    assert cat_worldbank == SourceCategory.OFFICIAL_GOVERNMENT
    assert calculate_domain_authority_score("worldbank.org", cat_worldbank) >= 0.90

    # Academic
    cat_edu = infer_source_category("mit.edu")
    assert cat_edu == SourceCategory.ACADEMIC_INSTITUTION
    assert calculate_domain_authority_score("mit.edu", cat_edu) >= 0.90

    # Company filing
    cat_sec = infer_source_category("sec.gov")
    assert cat_sec == SourceCategory.COMPANY_FILING
    assert calculate_domain_authority_score("sec.gov", cat_sec) >= 0.90

    # Industry Analyst
    cat_statista = infer_source_category("statista.com")
    assert cat_statista == SourceCategory.INDUSTRY_ANALYST
    assert calculate_domain_authority_score("statista.com", cat_statista) >= 0.85

    # Reputable News
    cat_reuters = infer_source_category("reuters.com")
    assert cat_reuters == SourceCategory.REPUTABLE_NEWS
    assert calculate_domain_authority_score("reuters.com", cat_reuters) >= 0.80

    # Generic
    cat_other = infer_source_category("randomblog.xyz")
    assert cat_other == SourceCategory.OTHER
    assert calculate_domain_authority_score("randomblog.xyz", cat_other) == 0.50


# ===========================================================================
# 3. COMPETITOR EXTRACTION TESTS
# ===========================================================================

def test_competitor_extraction_from_fetched_document():
    """Verify extraction service extracts competitor mentions with source provenance."""
    service = EvidenceExtractionService()
    doc_content = (
        "In the Indian online learning market, key players include Coursera, Udemy, and Scaler Academy. "
        "The market is expected to grow rapidly by 2026."
    )
    fetched_doc = FetchedSource(
        original_url="https://statista.com/market-report-edtech-india",
        final_url="https://statista.com/market-report-edtech-india",
        title="India EdTech Industry Outlook 2026",
        source_name="Statista",
        content=doc_content,
        fetch_status=FetchStatus.SUCCESS,
        lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
    )

    competitors = service.extract_competitors_from_source(fetched_doc)
    assert len(competitors) >= 2
    names = [c.name.lower() for c in competitors]
    assert any("coursera" in n for n in names)
    assert any("udemy" in n for n in names)
    assert any("scaler" in n for n in names)

    for c in competitors:
        assert c.source_url == "https://statista.com/market-report-edtech-india"
        assert c.source_name == "Statista"


def test_competitor_extraction_empty_when_no_competitors_mentioned():
    """Verify extraction service returns an empty list when document has no competitor claims."""
    service = EvidenceExtractionService()
    doc_content = "The total population of college students in India is 40 million in 2024."
    fetched_doc = FetchedSource(
        original_url="https://education.gov.in/aishe",
        title="AISHE Report",
        content=doc_content,
        fetch_status=FetchStatus.SUCCESS,
        lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
    )

    competitors = service.extract_competitors_from_source(fetched_doc)
    assert competitors == []


# ===========================================================================
# 4. PERSISTENCE LAYER TESTS
# ===========================================================================

def test_sqlite_persistence_crud_operations(tmp_path):
    """Verify SQLite repository saves, retrieves, lists, and deletes analyses cleanly."""
    db_file = str(tmp_path / "test_market_analyses.db")
    repo = AnalysisRepository(db_path=db_file)

    assert repo.count() == 0

    # 1. Save
    pipeline_res = PipelineResult(
        pipeline_id="pipe_test_123",
        status=PipelineStatus.COMPLETED,
        business_idea="An affordable coding school in India",
        business_analysis=BusinessAnalysis(
            business_idea="An affordable coding school in India",
            industry="EdTech",
            product="Coding school",
            target_customer="College students",
            geography="India",
        ),
        confidence="medium",
        competitors=[
            CompetitorInfo(
                name="Coursera",
                product_service="Online courses",
                source_url="https://statista.com/edtech",
            )
        ],
        warnings=["Sample warning"],
        errors=[],
        started_at="2026-09-13T12:00:00Z",
        completed_at="2026-09-13T12:00:05Z",
    )

    saved_id = repo.save(pipeline_res)
    assert saved_id == "pipe_test_123"
    assert repo.count() == 1

    # 2. Get by ID
    retrieved = repo.get_by_id("pipe_test_123")
    assert retrieved is not None
    assert retrieved["pipeline_id"] == "pipe_test_123"
    assert retrieved["business_idea"] == "An affordable coding school in India"
    assert retrieved["business_analysis"]["industry"] == "EdTech"
    assert len(retrieved.get("competitors", [])) == 1
    assert retrieved["competitors"][0]["name"] == "Coursera"

    # 3. List all
    listed = repo.list_all(limit=10, offset=0)
    assert len(listed) == 1
    assert listed[0]["analysis_id"] == "pipe_test_123"
    assert listed[0]["business_idea"] == "An affordable coding school in India"

    # 4. Delete
    deleted = repo.delete("pipe_test_123")
    assert deleted is True
    assert repo.count() == 0
    assert repo.get_by_id("pipe_test_123") is None


# ===========================================================================
# 5. API HISTORY & RETRIEVAL ENDPOINTS
# ===========================================================================

def test_api_pipeline_history_and_retrieval(tmp_path):
    """Verify GET /api/v1/pipeline/history and GET /api/v1/pipeline/{id}."""
    # List history
    resp_list = client.get("/api/v1/pipeline/history")
    assert resp_list.status_code == 200
    data = resp_list.json()
    assert "total" in data
    assert "items" in data

    # Retrieve non-existent ID
    resp_404 = client.get("/api/v1/pipeline/pipe_non_existent_999")
    assert resp_404.status_code == 404
    assert "not found" in resp_404.json()["detail"].lower()

    # Delete non-existent ID
    resp_del_404 = client.delete("/api/v1/pipeline/pipe_non_existent_999")
    assert resp_del_404.status_code == 404


# ===========================================================================
# 6. SOM SAFETY RULE PRESERVATION IN PIPELINE
# ===========================================================================

@pytest.mark.asyncio
async def test_som_safety_preservation_when_market_share_unavailable():
    """Verify SOM remains insufficient_evidence when empirical share is unavailable."""
    from app.orchestration.pipeline import MarketAnalysisPipeline

    pipeline = MarketAnalysisPipeline()
    req = PipelineRequest(
        business_idea="An affordable online programming platform for college students in India",
        enable_calculation=True,
    )

    # Mock Ollama and Discovery to provide student population and price, but NO obtainable market share
    with patch.object(
        pipeline.llm_service,
        "analyze_business_idea",
        new=AsyncMock(
            return_value=BusinessAnalysis(
                business_idea=req.business_idea,
                industry="EdTech",
                product="Online programming platform",
                target_customer="College students",
                geography="India",
            )
        ),
    ), patch.object(
        pipeline.discovery_service,
        "discover_sources",
        new=AsyncMock(
            return_value=MagicMock(
                sources=[
                    DiscoveredSource(
                        title="Higher Education Survey",
                        url="https://data.gov.in/higher-ed-stats",
                        domain="data.gov.in",
                        category=SourceCategory.OFFICIAL_GOVERNMENT,
                        lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
                        discovery_timestamp="2026-09-13T12:00:00Z",
                    )
                ]
            )
        ),
    ), patch.object(
        pipeline.fetch_service,
        "fetch_discovered_source",
        new=AsyncMock(
            return_value=FetchedSource(
                original_url="https://data.gov.in/higher-ed-stats",
                title="Higher Education Survey",
                content="There are 40 million college students in India. Course pricing averages 1200 INR per year.",
                fetch_status=FetchStatus.SUCCESS,
                lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
            )
        ),
    ):
        result = await pipeline.run(req)
        assert result.status in (PipelineStatus.COMPLETED, PipelineStatus.INSUFFICIENT_EVIDENCE, "completed", "insufficient_evidence")
        # SOM must be marked insufficient_evidence under SOM Safety Rule
        assert result.som is None or result.som.status in ("insufficient_evidence", "insufficient")
        assert result.som is None or result.som.estimate is None
