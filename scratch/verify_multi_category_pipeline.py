import asyncio
import json
import os
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.calculation import (
    BottomUpCalculationInputs,
    CalculationStatus,
    EvidenceInput,
    PriceFrequency,
    TopDownCalculationInputs,
)
from app.services.calculation_service import CalculationService
from app.taxonomy.b2b_saas import B2B_SAAS_TAXONOMY, get_category_by_id

def run_multi_category_verification():
    print("==================================================")
    print("RUNNING MULTI-CATEGORY B2B SAAS VERIFICATION SUITE")
    print("==================================================")
    
    client = TestClient(app)
    calc_service = CalculationService()
    
    # 1. API Health Checks
    print("\n--- 1. Testing Core Endpoints ---")
    r_root = client.get("/")
    assert r_root.status_code == 200
    print("[PASS] GET / -> 200 OK")
    
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "healthy"
    print("[PASS] GET /health -> 200 OK (healthy)")
    
    # 2. Testing Market Calculation Endpoint
    print("\n--- 2. Testing POST /api/v1/market/calculate ---")
    td = TopDownCalculationInputs(
        macro_market_size=EvidenceInput(
            name="Macro Market",
            value=10_000_000_000.0,
            unit="USD",
            currency="USD",
            source_quality_tier="TIER_1_GOVERNMENT_OFFICIAL",
        ),
        segment_percentages=[EvidenceInput(name="Target Segment", value=20.0, unit="%")],
        serviceable_geography_percentage=EvidenceInput(name="Geo Share", value=50.0, unit="%"),
        obtainable_market_share=EvidenceInput(name="Obtainable Share", value=5.0, unit="%"),
    )
    bu = BottomUpCalculationInputs(
        potential_customers=EvidenceInput(name="Potential Customers", value=100_000.0, unit="companies"),
        serviceable_customers=EvidenceInput(name="Serviceable Customers", value=25_000.0, unit="companies"),
        realistically_obtainable_customers=EvidenceInput(name="Obtainable Customers", value=1_000.0, unit="companies"),
        pricing=EvidenceInput(name="Annual ARPU", value=5_000.0, unit="USD", currency="USD", frequency=PriceFrequency.ANNUAL),
    )
    calc_resp = client.post("/api/v1/market/calculate", json={
        "top_down_inputs": td.model_dump(mode="json"),
        "bottom_up_inputs": bu.model_dump(mode="json"),
    })
    assert calc_resp.status_code == 200, f"Calc endpoint error: {calc_resp.text}"
    calc_data = calc_resp.json()
    assert calc_data["top_down_tam"]["estimate"] == 2_000_000_000.0
    assert calc_data["top_down_sam"]["estimate"] == 1_000_000_000.0
    assert calc_data["top_down_som"]["estimate"] == 50_000_000.0
    assert calc_data["bottom_up_tam"]["estimate"] == 500_000_000.0
    assert calc_data["bottom_up_sam"]["estimate"] == 125_000_000.0
    assert calc_data["bottom_up_som"]["estimate"] == 5_000_000.0
    print("[PASS] Deterministic Calculation API validated (Funnel Invariants SOM <= SAM <= TAM verified).")
    
    # 3. Test 3 Distinct B2B SaaS Categories through Pipeline & Calculation Engine
    categories_to_test = [
        {
            "category_id": "crm_sales",
            "category_name": "CRM & Sales",
            "idea": "B2B Sales CRM and Lead Intelligence platform for mid-market manufacturing enterprises in India",
            "macro_tam": 4_500_000_000.0,
            "segment_pct": 30.0,
            "geo_pct": 40.0,
            "obtainable_pct": 3.0,
            "customers": 40_000.0,
            "serviceable_cust": 12_000.0,
            "obtainable_cust": 360.0,
            "arpu": 6_000.0,
        },
        {
            "category_id": "hr_workforce",
            "category_name": "HR & Workforce Management",
            "idea": "Automated payroll, statutory compliance and workforce management SaaS for Indian SMBs",
            "macro_tam": 8_000_000_000.0,
            "segment_pct": 25.0,
            "geo_pct": 50.0,
            "obtainable_pct": 2.5,
            "customers": 200_000.0,
            "serviceable_cust": 50_000.0,
            "obtainable_cust": 1_250.0,
            "arpu": 1_200.0,
        },
        {
            "category_id": "healthcare_business_software",
            "category_name": "Healthcare Business Software",
            "idea": "Dental practice management, appointment scheduling, and digital imaging SaaS for private clinics in India",
            "macro_tam": 1_800_000_000.0,
            "segment_pct": 40.0,
            "geo_pct": 60.0,
            "obtainable_pct": 4.0,
            "customers": 50_000.0,
            "serviceable_cust": 20_000.0,
            "obtainable_cust": 800.0,
            "arpu": 1_500.0,
        },
    ]
    
    print("\n--- 3. Testing 3 Multi-Category B2B SaaS Scenarios ---")
    for idx, cat in enumerate(categories_to_test, 1):
        print(f"\n[Category {idx}/3: {cat['category_name']}]")
        print(f"  Idea: {cat['idea']}")
        
        # Verify taxonomy presence
        tax_entry = get_category_by_id(cat["category_id"])
        assert tax_entry is not None, f"Taxonomy entry missing for {cat['category_id']}"
        print(f"  [Taxonomy] Identified: {tax_entry.category_name} ({len(tax_entry.related_subcategories)} subcategories)")
        
        # Test Calculation
        td_test = TopDownCalculationInputs(
            macro_market_size=EvidenceInput(
                name=f"{cat['category_name']} Global/Regional Macro",
                value=cat["macro_tam"],
                unit="USD",
                currency="USD",
                source_quality_tier="TIER_1_GOVERNMENT_OFFICIAL",
            ),
            segment_percentages=[EvidenceInput(name="Target Segment Share", value=cat["segment_pct"], unit="%")],
            serviceable_geography_percentage=EvidenceInput(name="Target Geography Share", value=cat["geo_pct"], unit="%"),
            obtainable_market_share=EvidenceInput(name="Target Obtainable Share", value=cat["obtainable_pct"], unit="%"),
        )
        
        bu_test = BottomUpCalculationInputs(
            potential_customers=EvidenceInput(name="Potential Organizations", value=cat["customers"], unit="facilities"),
            serviceable_customers=EvidenceInput(name="Serviceable Segment Organizations", value=cat["serviceable_cust"], unit="facilities"),
            realistically_obtainable_customers=EvidenceInput(name="Obtainable Organizations", value=cat["obtainable_cust"], unit="facilities"),
            pricing=EvidenceInput(name="Annual ARPU", value=cat["arpu"], unit="USD", currency="USD", frequency=PriceFrequency.ANNUAL),
        )
        
        tam_td = calc_service.calculate_top_down_tam(td_test)
        sam_td = calc_service.calculate_top_down_sam(tam_td, td_test)
        som_td = calc_service.calculate_top_down_som(sam_td, td_test)
        
        tam_bu = calc_service.calculate_bottom_up_tam(bu_test)
        sam_bu = calc_service.calculate_bottom_up_sam(tam_bu, bu_test)
        som_bu = calc_service.calculate_bottom_up_som(sam_bu, bu_test)
        
        # Assert Top-Down Funnel Invariants
        assert tam_td.status == CalculationStatus.CALCULATED
        assert sam_td.status == CalculationStatus.CALCULATED
        assert som_td.status == CalculationStatus.CALCULATED
        assert som_td.estimate <= sam_td.estimate <= tam_td.estimate
        
        # Assert Bottom-Up Funnel Invariants
        assert tam_bu.status == CalculationStatus.CALCULATED
        assert sam_bu.status == CalculationStatus.CALCULATED
        assert som_bu.status == CalculationStatus.CALCULATED
        assert som_bu.estimate <= sam_bu.estimate <= tam_bu.estimate
        
        print(f"  [Top-Down]  TAM: ${tam_td.estimate:,.2f} | SAM: ${sam_td.estimate:,.2f} | SOM: ${som_td.estimate:,.2f}")
        print(f"  [Bottom-Up] TAM: ${tam_bu.estimate:,.2f} | SAM: ${sam_bu.estimate:,.2f} | SOM: ${som_bu.estimate:,.2f}")
        print(f"  [Funnel Invariants] Top-Down: {som_td.estimate} <= {sam_td.estimate} <= {tam_td.estimate} (VERIFIED)")
        print(f"  [Funnel Invariants] Bottom-Up: {som_bu.estimate} <= {sam_bu.estimate} <= {tam_bu.estimate} (VERIFIED)")
    
    print("\n==================================================")
    print("ALL 3 B2B SAAS CATEGORIES FULLY VERIFIED AND PASSING")
    print("==================================================")

if __name__ == "__main__":
    run_multi_category_verification()
