"""Live E2E Verification of Healthcare SaaS Market Sizing Engine (ClinicaFlow)."""
import asyncio
import json
import sys
import httpx

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

async def main():
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
        "sales_team_size": 2,
        "sales_cycle_months": 3.0,
        "geographic_reach_percentage": 100.0,
    }

    print("Submitting live pipeline analysis request for ClinicaFlow...")
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post("http://localhost:8000/api/v1/pipeline/analyze", json=payload)
        print(f"HTTP Status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Error: {resp.text}")
            return

        data = resp.json()
        print("\n================== LIVE E2E RESULT ==================")
        print(f"Pipeline ID: {data.get('pipeline_id')}")
        print(f"Status: {data.get('status')}")
        print(f"Provider: {data.get('research_provider')}")
        print(f"Confidence: {data.get('confidence')}")
        print(f"Evidence Quality: {data.get('evidence_quality_rating')}")

        tam = data.get("tam") or {}
        sam = data.get("sam") or {}
        som = data.get("som") or {}
        attractiveness = data.get("market_attractiveness") or {}

        print("\n--- TAM ---")
        print(f"Estimate: {tam.get('estimate')}")
        print(f"Display: {tam.get('display_value')}")
        print(f"Formula: {tam.get('formula')}")
        print(f"Potential Customers: {tam.get('inputs', {}).get('potential_customers')}")
        print(f"ARPU: {tam.get('inputs', {}).get('annual_revenue_per_customer')}")

        print("\n--- SAM ---")
        print(f"Estimate: {sam.get('estimate')}")
        print(f"Display: {sam.get('display_value')}")
        print(f"Formula: {sam.get('formula')}")
        print(f"Serviceable Customers: {sam.get('serviceable_customer_count')}")
        print(f"SAM % of TAM: {sam.get('sam_percentage_of_tam')}%")
        print(f"Constraints: {sam.get('serviceability_constraints')}")

        print("\n--- SOM ---")
        print(f"Estimate: {som.get('estimate')}")
        print(f"Display: {som.get('display_value')}")
        print(f"Formula: {som.get('formula')}")
        print(f"Obtainable Customers: {som.get('obtainable_customer_count')}")
        print(f"SOM % of SAM: {som.get('som_percentage_of_sam')}%")
        print(f"SOM Scenarios: {som.get('som_scenarios')}")

        print("\n--- ATTRACTIVENESS ---")
        print(f"Score: {attractiveness.get('score')} / 10")
        print(f"Rating: {attractiveness.get('rating')}")
        print(f"Explanation: {attractiveness.get('explanation')}")

        # Verification of Funnel Invariants
        tam_est = tam.get('estimate', 0)
        sam_est = sam.get('estimate', 0)
        som_est = som.get('estimate', 0)
        print("\n--- FUNNEL INVARIANT CHECK ---")
        print(f"TAM ({tam_est}) >= SAM ({sam_est}) >= SOM ({som_est}) >= 0: {tam_est >= sam_est >= som_est >= 0}")

if __name__ == "__main__":
    asyncio.run(main())
