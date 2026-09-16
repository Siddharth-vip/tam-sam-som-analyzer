import asyncio
import json
import httpx

async def run_clinicaflow():
    payload = {
        "business_name": "ClinicaFlow",
        "business_idea": "Cloud-based clinic management SaaS for small and medium-sized clinics in India.",
        "healthcare_saas_category": "Clinic Management SaaS",
        "customer_type": "Clinics",
        "target_country": "India",
        "pricing_basis": "per_facility",
        "per_facility_price": 48000.0,
        "serviceable_percentage": 30.0,
        "serviceability_criteria": ["Tier 1/2 cities", "EMR-ready clinics"],
        "max_sources": 5,
        "enable_calculation": True
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        print("Submitting ClinicaFlow analysis to http://localhost:8000/api/v1/pipeline/analyze...")
        response = await client.post("http://localhost:8000/api/v1/pipeline/analyze", json=payload)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("\n=== CLINICAFLOW ANALYSIS RESULTS ===")
            print(f"Pipeline ID: {data.get('pipeline_id')}")
            print(f"Status: {data.get('status')}")
            
            # TAM
            tam = data.get("tam") or (data.get("calculation_report") or {}).get("bottom_up_tam") or {}
            print("\n--- TAM (Total Addressable Market) ---")
            print(f"TAM Estimate: {tam.get('display_value') or tam.get('estimate')}")
            print(f"Formula: {tam.get('formula')}")
            print(f"Confidence: {tam.get('confidence')}")
            
            # SAM
            sam = data.get("sam") or (data.get("calculation_report") or {}).get("bottom_up_sam") or {}
            print("\n--- SAM (Serviceable Addressable Market) ---")
            print(f"SAM Estimate: {sam.get('display_value') or sam.get('estimate')}")
            print(f"SAM % of TAM: {sam.get('sam_percentage_of_tam')}%")
            print(f"Serviceable Customers: {sam.get('serviceable_customer_count')}")
            print(f"Serviceability Constraints: {sam.get('serviceability_constraints')}")
            print(f"Formula: {sam.get('formula')}")
            print(f"Confidence: {sam.get('confidence')}")
            print(f"Status: {sam.get('status')}")
            
            # Attractiveness
            attract = data.get("market_attractiveness") or {}
            print("\n--- Market Attractiveness ---")
            print(f"Rating: {attract.get('rating')} (Score: {attract.get('score')}/10)")
            print(f"Explanation: {attract.get('explanation')}")
            
            # Save raw result to file for audit
            with open("scratch/clinicaflow_result.json", "w") as f:
                json.dump(data, f, indent=2)
            print("\nSaved raw response to scratch/clinicaflow_result.json")
        else:
            print("Error response:", response.text)

if __name__ == "__main__":
    asyncio.run(run_clinicaflow())
