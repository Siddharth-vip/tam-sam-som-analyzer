from typing import Any, Dict
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.business import BusinessAnalysis, BusinessIdeaRequest
from app.services.llm_service import OllamaLLMService

client = TestClient(app)


# ---------------------------------------------------------------------------
# Unit tests for Pydantic Schemas
# ---------------------------------------------------------------------------

def test_business_idea_request_valid() -> None:
    req = BusinessIdeaRequest(business_idea="  An AI market research platform  ")
    assert req.business_idea == "An AI market research platform"


def test_business_idea_request_empty_rejected() -> None:
    with pytest.raises(ValueError):
        BusinessIdeaRequest(business_idea="")


def test_business_idea_request_whitespace_rejected() -> None:
    with pytest.raises(ValueError):
        BusinessIdeaRequest(business_idea="    \t \n  ")


def test_business_idea_request_too_short_rejected() -> None:
    with pytest.raises(ValueError):
        BusinessIdeaRequest(business_idea="ab")


def test_business_analysis_schema_nullable_fields() -> None:
    analysis = BusinessAnalysis(
        business_idea="A generic food delivery app",
        industry="Food Delivery",
        product="Delivery App",
        target_customer=None,
        geography=None,
        business_model=None,
        pricing_model=None,
        customer_problem=None,
        value_proposition=None,
    )
    assert analysis.geography is None
    assert analysis.pricing_model is None
    assert analysis.business_idea == "A generic food delivery app"


# ---------------------------------------------------------------------------
# API Endpoint Tests (with mocked Ollama HTTP calls)
# ---------------------------------------------------------------------------

def test_analyze_valid_business_idea() -> None:
    """TEST: Valid business idea returns 200 and structured data."""
    mock_llm_json_content = (
        '{"business_idea": "An affordable online programming platform for college students in India",'
        '"industry": "EdTech",'
        '"product": "Online programming platform",'
        '"target_customer": "College students in India",'
        '"geography": "India",'
        '"business_model": "B2C",'
        '"pricing_model": "Affordable subscription",'
        '"customer_problem": "High cost of coding education",'
        '"value_proposition": "Low-cost high-quality coding courses"}'
    )

    mock_ollama_response = {
        "model": "qwen3:8b",
        "message": {
            "role": "assistant",
            "content": mock_llm_json_content,
        },
        "done": True,
    }

    mock_response = httpx.Response(
        status_code=200,
        json=mock_ollama_response,
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        response = client.post(
            "/api/v1/business/analyze",
            json={"business_idea": "An affordable online programming platform for college students in India"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["industry"] == "EdTech"
        assert data["product"] == "Online programming platform"
        assert data["target_customer"] == "College students in India"
        assert data["geography"] == "India"
        assert data["business_model"] == "B2C"
        assert data["pricing_model"] == "Affordable subscription"
        assert data["customer_problem"] == "High cost of coding education"
        assert data["value_proposition"] == "Low-cost high-quality coding courses"


def test_analyze_empty_business_idea() -> None:
    """TEST: Empty business idea is rejected with 422."""
    response = client.post(
        "/api/v1/business/analyze",
        json={"business_idea": ""},
    )
    assert response.status_code == 422


def test_analyze_whitespace_only_business_idea() -> None:
    """TEST: Whitespace-only business idea is rejected with 422."""
    response = client.post(
        "/api/v1/business/analyze",
        json={"business_idea": "   \n\t   "},
    )
    assert response.status_code == 422


def test_analyze_missing_geography() -> None:
    """TEST: Idea with missing geography returns null for geography without inventing one."""
    mock_llm_json_content = (
        '{"business_idea": "I want to build a food delivery app",'
        '"industry": "Food Delivery / Online Food Ordering",'
        '"product": "Food delivery app",'
        '"target_customer": null,'
        '"geography": null,'
        '"business_model": null,'
        '"pricing_model": null,'
        '"customer_problem": null,'
        '"value_proposition": null}'
    )

    mock_ollama_response = {
        "model": "qwen3:8b",
        "message": {
            "role": "assistant",
            "content": mock_llm_json_content,
        },
        "done": True,
    }

    mock_response = httpx.Response(
        status_code=200,
        json=mock_ollama_response,
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        response = client.post(
            "/api/v1/business/analyze",
            json={"business_idea": "I want to build a food delivery app"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["geography"] is None
        assert data["pricing_model"] is None
        assert data["product"] == "Food delivery app"
        assert data["industry"] == "Food Delivery / Online Food Ordering"


def test_analyze_preserves_exact_user_business_idea() -> None:
    """TEST: Ensure exact business_idea string is preserved even if LLM shortens it."""
    input_text = "I want to build a B2C SaaS accounting platform for small businesses in India with a monthly subscription"
    mock_llm_json_content = (
        '{"business_idea": "B2C SaaS accounting platform",'
        '"industry": "Accounting Software / SaaS",'
        '"product": "SaaS accounting platform",'
        '"target_customer": "Small businesses",'
        '"geography": "India",'
        '"business_model": "B2C / SaaS",'
        '"pricing_model": "Monthly subscription",'
        '"customer_problem": null,'
        '"value_proposition": null}'
    )

    mock_ollama_response = {
        "model": "qwen3:8b",
        "message": {
            "role": "assistant",
            "content": mock_llm_json_content,
        },
        "done": True,
    }

    mock_response = httpx.Response(
        status_code=200,
        json=mock_ollama_response,
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        response = client.post(
            "/api/v1/business/analyze",
            json={"business_idea": input_text},
        )

        assert response.status_code == 200
        data = response.json()
        # Must preserve the exact user input string
        assert data["business_idea"] == input_text


# ---------------------------------------------------------------------------
# Phase 2.5 Specific Regression & Negative Tests
# ---------------------------------------------------------------------------

def test_regression_case_1_food_delivery_app() -> None:
    """Case 1: 'I want to build a food delivery app' -> product & industry not null, geography & pricing null."""
    mock_llm_json = (
        '{"business_idea": "I want to build a food delivery app",'
        '"industry": "Food Delivery / Online Food Ordering",'
        '"product": "Food delivery app",'
        '"target_customer": null,'
        '"geography": null,'
        '"business_model": null,'
        '"pricing_model": null,'
        '"customer_problem": null,'
        '"value_proposition": null}'
    )
    mock_resp = httpx.Response(
        status_code=200,
        json={"model": "qwen3:8b", "message": {"role": "assistant", "content": mock_llm_json}, "done": True},
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        response = client.post(
            "/api/v1/business/analyze",
            json={"business_idea": "I want to build a food delivery app"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["product"] is not None
        assert data["industry"] is not None
        assert data["geography"] is None
        assert data["pricing_model"] is None
        # Negative checks: Must NOT invent geography or pricing
        assert data["geography"] != "India"
        assert data["pricing_model"] != "commission"


def test_regression_case_2_food_delivery_chennai() -> None:
    """Case 2: 'I want to build a food delivery app for urban families in Chennai'."""
    mock_llm_json = (
        '{"business_idea": "I want to build a food delivery app for urban families in Chennai",'
        '"industry": "Food Delivery / Online Food Ordering",'
        '"product": "Food delivery app",'
        '"target_customer": "Urban families",'
        '"geography": "Chennai",'
        '"business_model": null,'
        '"pricing_model": null,'
        '"customer_problem": null,'
        '"value_proposition": null}'
    )
    mock_resp = httpx.Response(
        status_code=200,
        json={"model": "qwen3:8b", "message": {"role": "assistant", "content": mock_llm_json}, "done": True},
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        response = client.post(
            "/api/v1/business/analyze",
            json={"business_idea": "I want to build a food delivery app for urban families in Chennai"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["product"] is not None
        assert data["industry"] is not None
        assert "urban families" in data["target_customer"].lower()
        assert "chennai" in data["geography"].lower()
        assert data["pricing_model"] is None


def test_regression_case_3_saas_accounting_india() -> None:
    """Case 3: 'I want to build a B2C SaaS accounting platform for small businesses in India with a monthly subscription'."""
    full_input = "I want to build a B2C SaaS accounting platform for small businesses in India with a monthly subscription"
    mock_llm_json = (
        '{"business_idea": "B2C SaaS platform",'
        '"industry": "Accounting Software / SaaS / Financial Technology",'
        '"product": "SaaS accounting platform",'
        '"target_customer": "Small businesses",'
        '"geography": "India",'
        '"business_model": "B2C / SaaS",'
        '"pricing_model": "Monthly subscription",'
        '"customer_problem": null,'
        '"value_proposition": null}'
    )
    mock_resp = httpx.Response(
        status_code=200,
        json={"model": "qwen3:8b", "message": {"role": "assistant", "content": mock_llm_json}, "done": True},
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        response = client.post(
            "/api/v1/business/analyze",
            json={"business_idea": full_input},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["business_idea"] == full_input
        assert data["product"] is not None
        assert data["industry"] is not None
        assert "small businesses" in data["target_customer"].lower()
        assert "india" in data["geography"].lower()
        assert "monthly subscription" in data["pricing_model"].lower()


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------

def test_analyze_ollama_unavailable() -> None:
    """TEST: Ollama unavailable / connection error returns 503."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.ConnectError("Connection refused")):
        response = client.post(
            "/api/v1/business/analyze",
            json={"business_idea": "An affordable online programming platform"},
        )
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()


def test_analyze_ollama_timeout() -> None:
    """TEST: Ollama timeout returns 504."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.ReadTimeout("Request timed out")):
        response = client.post(
            "/api/v1/business/analyze",
            json={"business_idea": "An affordable online programming platform"},
        )
        assert response.status_code == 504
        assert "timed out" in response.json()["detail"].lower()


def test_analyze_ollama_invalid_json() -> None:
    """TEST: LLM returning invalid/unparseable JSON returns 502."""
    mock_ollama_response = {
        "model": "qwen3:8b",
        "message": {
            "role": "assistant",
            "content": "Not valid JSON at all",
        },
        "done": True,
    }
    mock_response = httpx.Response(
        status_code=200,
        json=mock_ollama_response,
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        response = client.post(
            "/api/v1/business/analyze",
            json={"business_idea": "An affordable online programming platform"},
        )
        assert response.status_code == 502
        assert "json" in response.json()["detail"].lower()


def test_analyze_ollama_empty_content() -> None:
    """TEST: LLM returning empty response returns 502."""
    mock_ollama_response = {
        "model": "qwen3:8b",
        "message": {
            "role": "assistant",
            "content": "",
        },
        "done": True,
    }
    mock_response = httpx.Response(
        status_code=200,
        json=mock_ollama_response,
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        response = client.post(
            "/api/v1/business/analyze",
            json={"business_idea": "An affordable online programming platform"},
        )
        assert response.status_code == 502
        assert "empty" in response.json()["detail"].lower()


def test_analyze_ollama_http_error() -> None:
    """TEST: Ollama returning non-200 status code returns 502."""
    mock_response = httpx.Response(
        status_code=500,
        text="Internal Ollama error",
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        response = client.post(
            "/api/v1/business/analyze",
            json={"business_idea": "An affordable online programming platform"},
        )
        assert response.status_code == 502


def test_regression_affordable_online_programming_platform_india() -> None:
    """TEST 1: 'I want to build an affordable online programming platform for college students in India'
    Layer 2 fills/verifies target customer, geography, industry, product, problem, and value prop, keeping pricing_model=None.
    """
    raw_idea = "I want to build an affordable online programming platform for college students in India"
    # Simulate LLM returning partial or null fields (the exact failure case reported)
    mock_llm_json = (
        '{"business_idea": "I want to build an affordable online programming platform for college students in India",'
        '"industry": null,'
        '"product": "Affordable online programming platform",'
        '"target_customer": null,'
        '"geography": null,'
        '"business_model": null,'
        '"pricing_model": null,'
        '"customer_problem": null,'
        '"value_proposition": null}'
    )
    mock_resp = httpx.Response(
        status_code=200,
        json={"model": "qwen3:8b", "message": {"role": "assistant", "content": mock_llm_json}, "done": True},
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        response = client.post(
            "/api/v1/business/analyze",
            json={"business_idea": raw_idea},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["business_idea"] == raw_idea
        assert data["product"] is not None
        assert "programming platform" in data["product"].lower()
        assert data["target_customer"] == "College students"
        assert data["geography"] == "India"
        assert data["industry"] is not None
        assert any(term in data["industry"].lower() for term in ("edtech", "education", "software"))
        assert data["business_model"] == "B2C"
        # Epistemic guard: 'affordable' is NOT a pricing model
        assert data["pricing_model"] is None
        # Inferred grounded problem & value proposition
        assert data["customer_problem"] is not None
        assert "affordable" in data["customer_problem"].lower() or "programming" in data["customer_problem"].lower()
        assert data["value_proposition"] is not None
        assert "coding" in data["value_proposition"].lower() or "programming" in data["value_proposition"].lower()


def test_regression_subscription_healthy_meal_delivery_chennai() -> None:
    """TEST 2: 'I want to create a subscription-based healthy meal delivery service for college students in Chennai.'
    Verifies subscription pricing model, B2C/Subscription business model, Chennai geography, and Food Delivery industry.
    """
    raw_idea = "I want to create a subscription-based healthy meal delivery service for college students in Chennai."
    # Simulate LLM returning partial nulls
    mock_llm_json = (
        '{"business_idea": "I want to create a subscription-based healthy meal delivery service for college students in Chennai.",'
        '"industry": null,'
        '"product": "Healthy meal delivery service",'
        '"target_customer": null,'
        '"geography": null,'
        '"business_model": null,'
        '"pricing_model": null,'
        '"customer_problem": null,'
        '"value_proposition": null}'
    )
    mock_resp = httpx.Response(
        status_code=200,
        json={"model": "qwen3:8b", "message": {"role": "assistant", "content": mock_llm_json}, "done": True},
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        response = client.post(
            "/api/v1/business/analyze",
            json={"business_idea": raw_idea},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["product"] is not None
        assert "meal delivery" in data["product"].lower()
        assert data["industry"] == "Food Delivery / Food Service"
        assert data["target_customer"] == "College students"
        assert data["geography"] == "Chennai"
        assert data["business_model"] in ("Subscription", "B2C")
        assert data["pricing_model"] == "Recurring Subscription"
        assert data["customer_problem"] is not None
        assert data["value_proposition"] is not None


def test_regression_vague_idea_preserves_null_fields() -> None:
    """TEST 3: A vague idea with insufficient information must return null rather than hallucinating."""
    raw_idea = "I want to build a generic platform"
    mock_llm_json = (
        '{"business_idea": "I want to build a generic platform",'
        '"industry": null,'
        '"product": null,'
        '"target_customer": null,'
        '"geography": null,'
        '"business_model": null,'
        '"pricing_model": null,'
        '"customer_problem": null,'
        '"value_proposition": null}'
    )
    mock_resp = httpx.Response(
        status_code=200,
        json={"model": "qwen3:8b", "message": {"role": "assistant", "content": mock_llm_json}, "done": True},
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        response = client.post(
            "/api/v1/business/analyze",
            json={"business_idea": raw_idea},
        )
        assert response.status_code == 200
        data = response.json()
        # Epistemic guard: Must NOT invent geography, target customer, or pricing
        assert data["geography"] is None
        assert data["target_customer"] is None
        assert data["pricing_model"] is None


def test_regression_qualitative_words_not_pricing_models() -> None:
    """TEST 4: Qualitative words ('affordable', 'premium', 'cheap', 'luxury') must NEVER become pricing_model."""
    ideas_to_test = [
        "A premium luxury watch marketplace for collectors",
        "A cheap budget-friendly grocery shopping app",
        "An affordable laundry service for busy professionals",
    ]
    for idea in ideas_to_test:
        mock_llm_json = (
            f'{{"business_idea": "{idea}",'
            '"industry": null,'
            '"product": null,'
            '"target_customer": null,'
            '"geography": null,'
            '"business_model": null,'
            '"pricing_model": "premium",'  # LLM erroneously outputs a qualitative word as pricing_model
            '"customer_problem": null,'
            '"value_proposition": null}'
        )
        mock_resp = httpx.Response(
            status_code=200,
            json={"model": "qwen3:8b", "message": {"role": "assistant", "content": mock_llm_json}, "done": True},
            request=httpx.Request("POST", "http://localhost:11434/api/chat"),
        )
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            response = client.post(
                "/api/v1/business/analyze",
                json={"business_idea": idea},
            )
            assert response.status_code == 200
            data = response.json()
            # Layer 2 must normalize away the qualitative word
            assert data["pricing_model"] is None


def test_regression_structured_json_with_nulls_passes_validation() -> None:
    """TEST 5: Verify valid Pydantic parsing and serialization when all optional fields are null."""
    mock_llm_json = (
        '{"business_idea": "Build something new",'
        '"industry": null,'
        '"product": null,'
        '"target_customer": null,'
        '"geography": null,'
        '"business_model": null,'
        '"pricing_model": null,'
        '"customer_problem": null,'
        '"value_proposition": null}'
    )
    mock_resp = httpx.Response(
        status_code=200,
        json={"model": "qwen3:8b", "message": {"role": "assistant", "content": mock_llm_json}, "done": True},
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        response = client.post(
            "/api/v1/business/analyze",
            json={"business_idea": "Build something new"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["business_idea"] == "Build something new"
        assert data["geography"] is None
        assert data["pricing_model"] is None
