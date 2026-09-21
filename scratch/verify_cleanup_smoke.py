import asyncio
import json
import os
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.calculation import (
    BottomUpCalculationInputs,
    CalculationInput,
    CalculationStatus,
    EvidenceInput,
    EvidenceQualityRating,
    PriceFrequency,
    TopDownCalculationInputs,
)
from app.services.calculation_service import CalculationService
from app.taxonomy.b2b_saas import B2B_SAAS_TAXONOMY

def run_smoke_test():
    print("=== STARTING SMOKE TEST ===")
    
    # 1. Test FastAPI app client
    client = TestClient(app)
    
    root_resp = client.get("/")
    assert root_resp.status_code == 200, f"Root endpoint failed: {root_resp.text}"
    print("[PASS] Root GET / returns 200 OK")
    
    health_resp = client.get("/health")
    assert health_resp.status_code == 200, f"Health endpoint failed: {health_resp.text}"
    health_data = health_resp.json()
    assert health_data["status"] == "healthy"
    print(f"[PASS] Health GET /health returns status: healthy (App: {health_data['app_name']})")
    
    # 2. Test Taxonomy
    assert len(B2B_SAAS_TAXONOMY) >= 25, f"Expected >= 25 categories, got {len(B2B_SAAS_TAXONOMY)}"
    print(f"[PASS] B2B SaaS Taxonomy verified: {len(B2B_SAAS_TAXONOMY)} categories present.")
    
    # 3. Test CalculationService (Authoritative TAM/SAM/SOM calculations)
    calc_service = CalculationService()
    
    # Top-Down Sizing
    td_inputs = TopDownCalculationInputs(
        macro_market_size=EvidenceInput(
            name="Global CRM Market",
            value=80_000_000_000.0,
            unit="USD",
            currency="USD",
            geography="Global",
            source_quality_tier="TIER_1_GOVERNMENT_OFFICIAL",
        ),
        segment_percentages=[
            EvidenceInput(
                name="SMB Segment",
                value=25.0,
                unit="%",
            )
        ],
        serviceable_geography_percentage=EvidenceInput(
            name="North America Share",
            value=40.0,
            unit="%",
        ),
        obtainable_market_share=EvidenceInput(
            name="Year 3 Target Share",
            value=2.0,
            unit="%",
        )
    )
    
    tam = calc_service.calculate_top_down_tam(td_inputs)
    assert tam.status == CalculationStatus.CALCULATED
    assert tam.estimate == 20_000_000_000.0  # 80B * 25% = 20B
    print(f"[PASS] Top-Down TAM Calculation: ${tam.estimate:,.2f}")
    
    sam = calc_service.calculate_top_down_sam(tam, td_inputs)
    assert sam.status == CalculationStatus.CALCULATED
    assert sam.estimate == 8_000_000_000.0   # 20B * 40% = 8B
    print(f"[PASS] Top-Down SAM Calculation: ${sam.estimate:,.2f}")
    
    som = calc_service.calculate_top_down_som(sam, td_inputs)
    assert som.status == CalculationStatus.CALCULATED
    assert som.estimate == 160_000_000.0     # 8B * 2% = 160M
    print(f"[PASS] Top-Down SOM Calculation: ${som.estimate:,.2f}")
    
    # Invariant verification: SOM <= SAM <= TAM
    assert som.estimate <= sam.estimate <= tam.estimate, "Funnel invariant violated!"
    print("[PASS] Funnel Invariants Verified: SOM <= SAM <= TAM")
    
    # Bottom-Up Sizing
    bu_inputs = BottomUpCalculationInputs(
        potential_customers=EvidenceInput(
            name="Target Mid-Market Businesses",
            value=50_000.0,
            unit="companies",
            entity_concept="business",
        ),
        serviceable_customers=EvidenceInput(
            name="Serviceable Mid-Market in Region",
            value=12_500.0,
            unit="companies",
            entity_concept="business",
        ),
        realistically_obtainable_customers=EvidenceInput(
            name="Target 3-Year Customers",
            value=500.0,
            unit="companies",
            entity_concept="business",
        ),
        pricing=EvidenceInput(
            name="Annual Contract Value",
            value=10_000.0,
            unit="USD",
            currency="USD",
            frequency=PriceFrequency.ANNUAL,
        )
    )
    
    tam_bu = calc_service.calculate_bottom_up_tam(bu_inputs)
    assert tam_bu.status == CalculationStatus.CALCULATED
    assert tam_bu.estimate == 500_000_000.0  # 50,000 * $10,000 = $500M
    print(f"[PASS] Bottom-Up TAM Calculation: ${tam_bu.estimate:,.2f}")
    
    sam_bu = calc_service.calculate_bottom_up_sam(tam_bu, bu_inputs)
    assert sam_bu.status == CalculationStatus.CALCULATED
    assert sam_bu.estimate == 125_000_000.0  # 12,500 * $10,000 = $125M
    print(f"[PASS] Bottom-Up SAM Calculation: ${sam_bu.estimate:,.2f}")
    
    som_bu = calc_service.calculate_bottom_up_som(sam_bu, bu_inputs)
    assert som_bu.status == CalculationStatus.CALCULATED
    assert som_bu.estimate == 5_000_000.0    # 500 * $10,000 = $5M
    print(f"[PASS] Bottom-Up SOM Calculation: ${som_bu.estimate:,.2f}")
    
    assert som_bu.estimate <= sam_bu.estimate <= tam_bu.estimate, "Bottom-up funnel invariant violated!"
    print("[PASS] Bottom-Up Funnel Invariants Verified: SOM <= SAM <= TAM")
    
    # Full Calculation Report API endpoint
    calc_req_payload = {
        "top_down_inputs": td_inputs.model_dump(mode="json"),
        "bottom_up_inputs": bu_inputs.model_dump(mode="json"),
    }
    calc_api_resp = client.post("/api/v1/market/calculate", json=calc_req_payload)
    assert calc_api_resp.status_code == 200, f"Calculation API failed: {calc_api_resp.text}"
    report = calc_api_resp.json()
    assert report["top_down_tam"]["estimate"] == 20_000_000_000.0
    print("[PASS] API POST /api/v1/market/calculate returns full verified calculation report")
    
    print("=== SMOKE TEST COMPLETED SUCCESSFULLY WITH 100% INVARIANTS INTACT ===")

if __name__ == "__main__":
    run_smoke_test()
