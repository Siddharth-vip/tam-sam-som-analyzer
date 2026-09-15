import asyncio
import json
import logging
from app.orchestration.pipeline import MarketAnalysisPipeline, PipelineRequest
from app.schemas.calculation import CalculationStatus

logging.basicConfig(level=logging.WARNING)

async def test_all_scenarios():
    pipeline = MarketAnalysisPipeline()

    scenarios = [
        # Required live scenarios
        ("Pet Care Service", "On-demand pet care and grooming platform for pet owners in urban India", "India"),
        ("Tutoring Platform", "Online high school tutoring and test prep platform for students in India", "India"),
        ("Food Delivery", "Online food delivery platform for college students in Tamil Nadu, India", "Tamil Nadu"),
        
        # 10 Sectors
        ("SaaS", "B2B accounting and invoice management SaaS for small businesses in India", "India"),
        ("Healthcare", "Telemedicine and digital doctor consultation platform for rural patients in India", "India"),
        ("FinTech", "Micro-lending and credit scoring platform for gig workers in Southeast Asia", "Southeast Asia"),
        ("EdTech", "Interactive coding and software engineering bootcamp for working professionals in India", "India"),
        ("Food Delivery", "30-minute grocery delivery service for working professionals in Tier-2 Indian cities", "India"),
        ("Solar", "Residential rooftop solar subscription and financing platform for homeowners in India", "India"),
        ("Logistics", "Cold-chain freight logistics and tracking platform for pharmaceutical companies in India", "India"),
        ("E-Commerce", "Direct-to-consumer sustainable apparel and fashion marketplace in Europe", "Europe"),
        ("Agriculture", "AI-powered soil testing and crop yield optimization platform for farmers in India", "India"),
        ("Manufacturing", "Industrial IoT energy monitoring and efficiency software for manufacturing plants in Germany", "Germany"),

        # 3 Unseen Concepts
        ("Unseen 1 - Predictive Maintenance", "I want to build a predictive maintenance SaaS for factories in India.", "India"),
        ("Unseen 2 - Remote Physiotherapy", "I want to build a remote physiotherapy platform for elderly patients in Europe.", "Europe"),
        ("Unseen 3 - AI Procurement", "I want to build an AI-powered procurement platform for medium-sized manufacturers.", "Global"),
    ]

    print("=" * 80)
    print("RUNNING COMPREHENSIVE DOMAIN-AGNOSTIC VALIDATION SUITE")
    print("=" * 80)

    results = []

    for name, idea, geo in scenarios:
        req = PipelineRequest(business_idea=idea, preferred_geography=geo, preferred_year=2025)
        res = await pipeline.run(req)

        analysis = res.business_analysis
        calc = res.calculation_report
        tam = res.tam
        sam = res.sam
        som = res.som

        status_str = res.status.value if hasattr(res.status, "value") else str(res.status)
        tam_val = f"{tam.currency or '$'} {tam.estimate:,.0f}" if (tam and tam.estimate) else "N/A"
        sam_val = f"{sam.currency or '$'} {sam.estimate:,.0f}" if (sam and sam.estimate) else "N/A"
        som_val = f"{som.currency or '$'} {som.estimate:,.0f}" if (som and som.estimate) else "N/A"

        tam_status = tam.status if tam else "N/A"
        sam_status = sam.status if sam else "N/A"
        som_status = som.status if som else "N/A"

        market_def = calc.market_definition if calc else (analysis.market_definition if analysis else "N/A")
        tam_meth = calc.tam_methodology if calc else "N/A"
        sam_meth = calc.sam_methodology if calc else "N/A"
        som_meth = calc.som_methodology if calc else "N/A"

        # Check safety invariants
        inv_bounds = True
        if tam and sam and tam.estimate and sam.estimate:
            if sam.estimate > tam.estimate:
                inv_bounds = False
        if sam and som and sam.estimate and som.estimate:
            if som.estimate > sam.estimate:
                inv_bounds = False

        record = {
            "name": name,
            "idea": idea,
            "geography": geo,
            "sector": getattr(analysis, "sector", None),
            "industry": getattr(analysis, "industry", None),
            "product": getattr(analysis, "product", None),
            "market_definition": market_def,
            "tam_status": str(tam_status),
            "tam_estimate": tam_val,
            "tam_methodology": tam_meth,
            "sam_status": str(sam_status),
            "sam_estimate": sam_val,
            "sam_methodology": sam_meth,
            "som_status": str(som_status),
            "som_estimate": som_val,
            "som_methodology": som_meth,
            "invariants_passed": inv_bounds,
            "pipeline_status": status_str,
        }
        results.append(record)

        print(f"\n--- Scenario: {name} ---", flush=True)
        print(f"Idea: {idea}", flush=True)
        print(f"Sector: {record['sector']} | Industry: {record['industry']}", flush=True)
        print(f"Market Definition: {market_def}", flush=True)
        print(f"TAM: {tam_val} ({tam_status}) via {tam_meth}", flush=True)
        print(f"SAM: {sam_val} ({sam_status}) via {sam_meth}", flush=True)
        print(f"SOM: {som_val} ({som_status}) via {som_meth}", flush=True)
        print(f"Invariants Enforced (0 <= SOM <= SAM <= TAM): {inv_bounds}", flush=True)

    # Summary table
    print("\n" + "=" * 80, flush=True)
    print("COMPREHENSIVE VALIDATION SUMMARY", flush=True)
    print("=" * 80, flush=True)
    for r in results:
        inv_str = "PASS" if r['invariants_passed'] else "FAIL"
        print(f"{r['name']:<30} | TAM: {r['tam_estimate']:<16} | SAM: {r['sam_estimate']:<16} | SOM: {r['som_estimate']:<16} | Invariants: {inv_str}", flush=True)

    with open("scratch/validation_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(test_all_scenarios())
