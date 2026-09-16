"""Multi-Business QA Audit Test Script for TAM -> SAM -> SOM Pipeline."""
import asyncio
import sys
import httpx

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

TEST_BUSINESSES = [
    {
        "name": "ClinicaFlow",
        "payload": {
            "business_name": "ClinicaFlow",
            "business_idea": "Cloud-based clinic management SaaS for small and medium-sized outpatient clinics in India.",
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
    },
    {
        "name": "MedSchedule",
        "payload": {
            "business_name": "MedSchedule",
            "business_idea": "Automated patient appointment scheduling and reminder SaaS for specialized clinics in India.",
            "healthcare_saas_category": "Appointment Scheduling & Practice Management SaaS",
            "customer_type": "Clinics",
            "target_country": "India",
            "pricing_basis": "per_facility",
            "monthly_price": 2500.0,
            "serviceable_percentage": 25.0,
            "serviceability_criteria": ["High-volume clinics"],
            "sales_team_size": 3,
            "sales_cycle_months": 2.0,
            "geographic_reach_percentage": 50.0,
        }
    },
    {
        "name": "PharmTrack",
        "payload": {
            "business_name": "PharmTrack",
            "business_idea": "Hospital inpatient pharmacy inventory and barcode medication administration SaaS in India.",
            "healthcare_saas_category": "Hospital Pharmacy Management SaaS",
            "customer_type": "Hospitals",
            "target_country": "India",
            "pricing_basis": "per_facility",
            "annual_price": 240000.0,
            "serviceable_percentage": 20.0,
            "serviceability_criteria": ["Tertiary care hospitals >100 beds"],
            "sales_team_size": 4,
            "sales_cycle_months": 6.0,
            "geographic_reach_percentage": 100.0,
        }
    },
    {
        "name": "RadioCloud",
        "payload": {
            "business_name": "RadioCloud",
            "business_idea": "Cloud PACS and teleradiology workflow SaaS for imaging centers and diagnostic laboratories in India.",
            "healthcare_saas_category": "Diagnostic & Laboratory Management SaaS",
            "customer_type": "Diagnostic Laboratories",
            "target_country": "India",
            "pricing_basis": "per_facility",
            "annual_price": 180000.0,
            "serviceable_percentage": 35.0,
            "serviceability_criteria": ["NABL-accredited diagnostic labs"],
            "sales_team_size": 2,
            "sales_cycle_months": 4.0,
            "geographic_reach_percentage": 75.0,
        }
    }
]

async def run_audit():
    print("=================================================================")
    print("STARTING MULTI-BUSINESS AUDIT (4 DISTINCT HEALTHCARE SAAS DOMAINS)")
    print("=================================================================")

    async with httpx.AsyncClient(timeout=180.0) as client:
        for b in TEST_BUSINESSES:
            print(f"\n[AUDITING] {b['name']} ({b['payload']['healthcare_saas_category']})...")
            resp = await client.post("http://localhost:8000/api/v1/pipeline/analyze", json=b["payload"])
            if resp.status_code != 200:
                print(f"FAILED: HTTP {resp.status_code} - {resp.text}")
                continue

            data = resp.json()
            tam = data.get("tam") or {}
            sam = data.get("sam") or {}
            som = data.get("som") or {}
            attr = data.get("market_attractiveness") or {}

            tam_val = tam.get("estimate") or 0.0
            sam_val = sam.get("estimate") or 0.0
            som_val = som.get("estimate") or 0.0

            n_pot = tam.get("inputs", {}).get("potential_customers", {}).get("value") or 0.0
            n_srv = sam.get("serviceable_customer_count") or 0.0
            n_obt = som.get("obtainable_customer_count") or 0.0
            arpu = tam.get("inputs", {}).get("annual_revenue_per_customer", {}).get("value") or 0.0

            # Manual recalculation check
            tam_manual = n_pot * arpu
            sam_manual = n_srv * arpu
            som_manual = n_obt * arpu

            print(f"  Status: {data.get('status')} | Provider: {data.get('research_provider')}")
            print(f"  Customer Funnel: N_pot={n_pot:,.0f} -> N_srv={n_srv:,.0f} -> N_obt={n_obt:,.0f}")
            print(f"  Valuation Funnel: TAM={tam.get('display_value')} -> SAM={sam.get('display_value')} -> SOM={som.get('display_value')}")
            print(f"  Attractiveness Score: {attr.get('score')}/10 ({attr.get('rating')})")
            
            # Verifications
            inv_customers = (n_pot >= n_srv >= n_obt >= 0)
            inv_market = (tam_val >= sam_val >= som_val >= 0)
            tam_correct = abs(tam_val - tam_manual) < 1.0
            sam_correct = abs(sam_val - sam_manual) < 1.0
            som_correct = abs(som_val - som_manual) < 1.0

            print(f"  [CHECK] Customer Funnel Valid (N_pot >= N_srv >= N_obt): {inv_customers}")
            print(f"  [CHECK] Market Funnel Valid (TAM >= SAM >= SOM): {inv_market}")
            print(f"  [CHECK] TAM Determinism (TAM == N_pot * ARPU): {tam_correct} ({tam_val:,.0f} vs {tam_manual:,.0f})")
            print(f"  [CHECK] SAM Determinism (SAM == N_srv * ARPU): {sam_correct} ({sam_val:,.0f} vs {sam_manual:,.0f})")
            print(f"  [CHECK] SOM Determinism (SOM == N_obt * ARPU): {som_correct} ({som_val:,.0f} vs {som_manual:,.0f})")

if __name__ == "__main__":
    asyncio.run(run_audit())
