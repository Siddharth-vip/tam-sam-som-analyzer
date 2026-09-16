import json
from app.storage.repository import PipelineRunRepository

repo = PipelineRunRepository()
record = repo.get_by_id("pipe_bab6f6d9dd1d")

if record:
    print("=== CLINICAFLOW PIPELINE RUN (pipe_bab6f6d9dd1d) ===")
    print(f"Status: {record.get('status')}")
    print(f"Business: {record.get('business_analysis', {}).get('business_name')}")
    print(f"Category: {record.get('business_analysis', {}).get('healthcare_saas_category')}")
    print(f"Customer Type: {record.get('business_analysis', {}).get('customer_type')}")
    print(f"Target Country: {record.get('business_analysis', {}).get('target_country')}")
    
    # TAM
    tam = record.get("tam") or {}
    print("\n--- 1. TAM (Total Addressable Market) ---")
    print(f"Valuation: INR {tam.get('estimate', 0):,.2f} ({tam.get('display_value')})")
    print(f"Formula: {tam.get('formula')}")
    print(f"Confidence: {tam.get('confidence')}")
    print(f"Evidence Quality: {tam.get('evidence_quality')}")
    print("TAM Inputs:")
    for k, v in (tam.get("inputs") or {}).items():
        if isinstance(v, dict):
            print(f"  - {k}: {v.get('value')} {v.get('unit')} [Data Type: {v.get('data_type')}, Source: {v.get('source')}, URL: {v.get('source_url')}]")
        else:
            print(f"  - {k}: {v}")

    # SAM
    sam = record.get("sam") or {}
    print("\n--- 2. SAM (Serviceable Addressable Market) ---")
    print(f"Valuation: INR {sam.get('estimate', 0):,.2f} ({sam.get('display_value')})")
    print(f"Serviceable Customer Population: {sam.get('serviceable_customer_count'):,.0f} clinics")
    print(f"Serviceability Factor: {sam.get('sam_percentage_of_tam')}% of TAM")
    print(f"Serviceability Constraints Applied: {sam.get('serviceability_constraints')}")
    print(f"Formula: {sam.get('formula')}")
    print(f"Confidence: {sam.get('confidence')}")
    print(f"Status: {sam.get('status')}")
    print("SAM Inputs:")
    for k, v in (sam.get("inputs") or {}).items():
        if isinstance(v, dict):
            print(f"  - {k}: {v.get('value')} {v.get('unit')} [Data Type: {v.get('data_type')}, Source: {v.get('source')}, URL: {v.get('source_url')}]")
        else:
            print(f"  - {k}: {v}")

    # Calculation Steps Trace
    print("\n--- 3. SAM Calculation Step Trace ---")
    for step in sam.get("steps", []):
        print(f"  Step {step.get('step_number')}: {step.get('description')}")
        print(f"    Formula: {step.get('formula')}")
        print(f"    Operands: {step.get('operands')}")
        print(f"    Result: {step.get('result'):,.2f} {step.get('unit')}")

    # Market Attractiveness
    attract = record.get("market_attractiveness") or {}
    print("\n--- 4. Market Attractiveness ---")
    print(f"Rating: {attract.get('rating')} (Score: {attract.get('score')}/10)")
    print(f"Explanation: {attract.get('explanation')}")
else:
    print("Record pipe_bab6f6d9dd1d not found.")
