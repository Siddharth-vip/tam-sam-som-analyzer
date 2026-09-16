import httpx
import json

payload = {
    "business_idea": "Cloud-based clinic management SaaS for small and medium-sized clinics in India.",
    "business_name": "ClinicaFlow",
    "healthcare_saas_category": "Clinic Management SaaS",
    "customer_type": "clinics",
    "target_country": "India",
    "pricing_basis": "per_facility",
    "per_facility_price": 48000,
    "clinical_or_non_clinical": "clinical",
    "regulatory_market": "ABDM / NABH Compliant",
    "emr_integration_required": True,
    "preferred_geography": "India",
    "max_sources": 5,
    "enable_calculation": True,
}

print("Sending request to Vite frontend proxy: http://localhost:5173/api/v1/pipeline/analyze")
with httpx.Client(timeout=180.0) as client:
    r = client.post("http://localhost:5173/api/v1/pipeline/analyze", json=payload)
    print("HTTP Status:", r.status_code)
    data = r.json()
    print("Pipeline ID:", data.get("pipeline_id"))
    print("Status:", data.get("status"))
    print("Category:", data.get("business_analysis", {}).get("category"))
    print("Target Audience:", data.get("business_analysis", {}).get("target_audience"))
    print("TAM Bottom-Up:", data.get("tam", {}).get("bottom_up_tam"))
    print("TAM Top-Down:", data.get("tam", {}).get("top_down_tam"))
    print("Currency:", data.get("calculation_report", {}).get("currency"))
    print("Research Provider:", data.get("research_provider"))
    print("Discovered Sources Count:", len(data.get("discovered_sources", [])))
    for s in data.get("discovered_sources", []):
        print(f"  - Source: {s.get('name')} | URL: {s.get('url')} | Type: {s.get('data_type')}")
    print("Validation Results Count:", len(data.get("validation_results", [])))
    for v in data.get("validation_results", []):
        print(f"  - Val: {v.get('source_name')} | Suitable: {v.get('is_suitable')} | Score: {v.get('suitability_score')} | Reason: {v.get('suitability_reason')}")
    print("Assumptions Count:", len(data.get("calculation_report", {}).get("all_assumptions", [])))
    for a in data.get("calculation_report", {}).get("all_assumptions", []):
        print(f"  - Assumption: {a.get('field_name')} = {a.get('value')} {a.get('unit')} ({a.get('data_type')}) [Source: {a.get('source')}]")
    print("Steps Count:", len(data.get("calculation_report", {}).get("all_steps", [])))
    for step in data.get("calculation_report", {}).get("all_steps", []):
        print(f"  - Step {step.get('step_number')}: {step.get('description')} = {step.get('result_value')} {step.get('unit')} (Formula: {step.get('formula')})")
