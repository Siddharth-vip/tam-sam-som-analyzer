import sys
import io
import time
import httpx
import json

# Ensure stdout handles unicode/rupee cleanly
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_pipeline(business_name, idea, category, customer_type, country, pricing_basis, price):
    payload = {
        "business_idea": idea,
        "business_name": business_name,
        "healthcare_saas_category": category,
        "customer_type": customer_type,
        "target_country": country,
        "pricing_basis": pricing_basis,
        "per_facility_price": price if pricing_basis == "per_facility" else None,
        "annual_subscription_price": price if pricing_basis == "subscription_annual" else None,
        "clinical_or_non_clinical": "clinical",
        "regulatory_market": "ABDM / NABH Compliant",
        "emr_integration_required": True,
        "preferred_geography": country,
        "max_sources": 5,
        "enable_calculation": True,
    }
    print(f"\n==========================================")
    print(f"Testing {business_name} on http://localhost:8000/api/v1/pipeline/analyze")
    print(f"==========================================")
    t0 = time.time()
    with httpx.Client(timeout=180.0) as client:
        r = client.post("http://localhost:8000/api/v1/pipeline/analyze", json=payload)
    elapsed = time.time() - t0
    print(f"Response in {elapsed:.2f}s | HTTP Status: {r.status_code}")
    if r.status_code != 200:
        print("Error Response:", r.text)
        return None
    data = r.json()
    print("Pipeline ID:", data.get("pipeline_id"))
    print("Status:", data.get("status"))
    print("Business Analysis:")
    ba = data.get("business_analysis", {})
    print("  Healthcare SaaS Category:", ba.get("healthcare_saas_category"))
    print("  Customer Type:", ba.get("customer_type"))
    print("  Target Customer:", ba.get("target_customer"))
    print("  Target Country:", ba.get("target_country"))
    print("  Pricing Basis:", ba.get("pricing_basis"))
    print("  Annual Revenue per Customer:", ba.get("annual_revenue_per_customer"))
    print("  Clinical Use:", ba.get("clinical_use"))
    print("  Regulatory Market:", ba.get("regulatory_market"))
    print("Research Provider:", data.get("research_provider"))
    print(f"Discovered Sources ({len(data.get('discovered_sources', []))}):")
    for s in data.get("discovered_sources", []):
        print(f"  - [{s.get('data_type')}] {s.get('name')}: {s.get('url')} (Year: {s.get('published_year')})")
    print(f"Validation Results ({len(data.get('validation_results', []))}):")
    for v in data.get("validation_results", []):
        if v.get("is_suitable"):
            print(f"  - SUITABLE: {v.get('source_name')} | Metric: {v.get('metric_type')} | Value: {v.get('value')} {v.get('unit')} | Score: {v.get('suitability_score')} | Reason: {v.get('suitability_reason')}")
        else:
            print(f"  - REJECTED: {v.get('source_name')} | Metric: {v.get('metric_type')} | Value: {v.get('value')} {v.get('unit')} | Score: {v.get('suitability_score')} | Reason: {v.get('suitability_reason')}")
    calc = data.get("calculation_report", {})
    print("Calculation Report:")
    print("  Currency:", calc.get("currency"))
    print("  TAM Summary:")
    tam = data.get("tam", {})
    print(f"    * Bottom-Up TAM: {tam.get('bottom_up_tam')} {tam.get('currency')} (Method: {tam.get('tam_method')}, Confidence: {tam.get('confidence_score')})")
    print(f"    * Top-Down TAM: {tam.get('top_down_tam')} {tam.get('currency')} (Status: {tam.get('status')})")
    print("  All Assumptions:")
    for a in calc.get("all_assumptions", []):
        print(f"    * {a.get('field_name')} = {a.get('value')} {a.get('unit')} [{a.get('data_type')}] Source: {a.get('source')} (URL: {a.get('source_url')})")
    print("  Calculation Steps:")
    for s in calc.get("all_steps", []):
        print(f"    * Step {s.get('step_number')}: {s.get('description')} -> {s.get('result_value')} {s.get('unit')} (Formula: {s.get('formula')})")
    print("Attractiveness:", data.get("market_attractiveness"))
    print("Warnings:", data.get("warnings"))
    print("Errors:", data.get("errors"))
    return data

if __name__ == "__main__":
    # Test 1: ClinicaFlow
    test_pipeline(
        business_name="ClinicaFlow",
        idea="Cloud-based clinic management SaaS for small and medium-sized clinics in India.",
        category="Clinic Management SaaS",
        customer_type="clinics",
        country="India",
        pricing_basis="per_facility",
        price=48000,
    )

    # Test 2: MediSchedule
    test_pipeline(
        business_name="MediSchedule",
        idea="Cloud-based appointment and scheduling SaaS for outpatient clinics in India.",
        category="Clinic Management SaaS",
        customer_type="clinics",
        country="India",
        pricing_basis="per_facility",
        price=36000,
    )
