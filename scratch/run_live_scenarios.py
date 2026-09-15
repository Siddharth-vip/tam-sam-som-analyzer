import sys
import os
sys.path.insert(0, os.path.abspath("."))
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from app.orchestration.models import PipelineRequest
from app.orchestration.pipeline import MarketAnalysisPipeline
from app.schemas.business import BusinessAnalysis
from app.discovery.mock_provider import MockDiscoveryProvider
from app.fetching.models import FetchedSource, FetchStatus
from app.schemas.discovery import DiscoveredSource, SourceCategory, SourceQualityTier, DiscoveryLifecycleStage, DiscoveryResponse, DiscoveryStatus, ResearchQuery
from app.schemas.calculation import CalculationAssumption
from app.services.discovery_service import DiscoveryService
from app.services.fetch_service import SourceFetchService
from app.services.extraction_service import EvidenceExtractionService
from app.services.validation_service import EvidenceValidationService
from app.services.calculation_service import CalculationService
from app.services.llm_service import OllamaLLMService


async def run_scenario_1():
    # Scenario 1: India pet-care service platform
    mock_llm = MagicMock(spec=OllamaLLMService)
    mock_llm.analyze_business_idea = AsyncMock(
        return_value=BusinessAnalysis(
            business_idea="Online pet care and grooming service platform connecting pet owners with certified groomers across India",
            product="Pet care and grooming service platform",
            industry="Pet Care / Pet Services",
            target_customer="Urban pet owners",
            geography="India",
            pricing_model="Transaction fee / subscription",
            business_model="B2C Marketplace / Services",
        )
    )
    mock_llm.generate_research_queries = AsyncMock(return_value=[
        ResearchQuery(metric_required="market size", industry_topic="Pet Care", geography="India", year=2024)
    ])

    raw_text = (
        "The overall pet care market in India reached $800 million in 2024. "
        "Pet owners in India spend an average of $29.5 per customer annually on grooming items. "
        "The global pet care market was valued at $14.8 billion in 2024, with US market size at $8.2 billion. "
        "Pet care market in India is expanding at a CAGR of 19.2% per year. "
        "Furthermore, 65% of households in urban India own dogs rather than cats. "
        "Pet food products represent 70% of total pet care sales, while pet grooming and veterinary services account for 18% of the total pet care market in India."
    )

    discovered = [
        DiscoveredSource(
            title="India Pet Care Market Size & Services Overview",
            url="https://marketresearch.in/pet-care-india-2024",
            snippet="India pet care market is estimated at $800 million in 2024. Pet grooming and veterinary services account for 18% of the total pet care market in India.",
            mock_content=raw_text,
            source_name="India Market Research",
            category=SourceCategory.INDUSTRY_ANALYST,
            source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
            lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
            relevance_score=0.92,
        )
    ]

    fetched = [
        FetchedSource(
            original_url="https://marketresearch.in/pet-care-india-2024",
            final_url="https://marketresearch.in/pet-care-india-2024",
            title="India Pet Care Market Size & Services Overview",
            raw_content=raw_text,
            extracted_text=raw_text,
            content=raw_text,
            fetch_status=FetchStatus.SUCCESS,
            status_code=200,
            content_length=len(raw_text),
            category=SourceCategory.INDUSTRY_ANALYST,
            source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
            lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
        )
    ]

    discovery_svc = DiscoveryService(provider=MockDiscoveryProvider(seeded_sources=discovered))

    mock_fetcher = MagicMock(spec=SourceFetchService)
    mock_fetcher.fetch_all = AsyncMock(return_value=fetched)
    mock_fetcher.fetch_discovered_source = AsyncMock(return_value=fetched[0])

    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm,
        discovery_service=discovery_svc,
        fetch_service=mock_fetcher,
        extraction_service=EvidenceExtractionService(),
        validation_service=EvidenceValidationService(),
        calculation_service=CalculationService(),
    )

    req = PipelineRequest(
        business_idea="Online pet care and grooming service platform connecting pet owners with certified groomers across India",
        target_geography="India",
        target_year=2024,
    )

    result = await pipeline.run(req)
    return "India pet-care service platform", result, raw_text


async def run_scenario_2():
    # Scenario 2: India high-school tutoring platform
    mock_llm = MagicMock(spec=OllamaLLMService)
    mock_llm.analyze_business_idea = AsyncMock(
        return_value=BusinessAnalysis(
            business_idea="High-school online tutoring and test prep platform for students in India",
            product="High-school tutoring platform",
            industry="Education / Online Tutoring",
            target_customer="High-school students",
            geography="India",
            pricing_model="Monthly subscription",
            business_model="B2C EdTech",
        )
    )
    mock_llm.generate_research_queries = AsyncMock(return_value=[
        ResearchQuery(metric_required="market size", industry_topic="Online Tutoring", geography="India", year=2024)
    ])

    raw_text = (
        "The total tutoring and supplemental education market in India reached USD 1.8 billion in 2024. "
        "Average student annual subscription price is $45 per student per year. "
        "In comparison, the tutoring market in China reached $12 billion in 2024. "
        "EdTech sector is growing at a compound annual growth rate CAGR of 15.4% through 2028. "
        "Demographic survey shows 52% of high school students are male and 48% are female. "
        "Secondary and high-school tutoring (grades 9-12) accounts for 28% of the tutoring market in India. "
        "Discount promotions of 30% are common during back-to-school season."
    )

    discovered = [
        DiscoveredSource(
            title="India K-12 Tutoring & EdTech Market Report 2024",
            url="https://edtechindia.org/reports/k12-tutoring-2024",
            snippet="The tutoring and test prep market in India was valued at USD 1.8 billion in 2024. High-school secondary tutoring represents 28% of the tutoring market in India.",
            mock_content=raw_text,
            source_name="EdTech India Association",
            category=SourceCategory.INDUSTRY_ANALYST,
            source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
            lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
            relevance_score=0.95,
        )
    ]

    fetched = [
        FetchedSource(
            original_url="https://edtechindia.org/reports/k12-tutoring-2024",
            final_url="https://edtechindia.org/reports/k12-tutoring-2024",
            title="India K-12 Tutoring & EdTech Market Report 2024",
            raw_content=raw_text,
            extracted_text=raw_text,
            content=raw_text,
            fetch_status=FetchStatus.SUCCESS,
            status_code=200,
            content_length=len(raw_text),
            category=SourceCategory.INDUSTRY_ANALYST,
            source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
            lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
        )
    ]

    discovery_svc = DiscoveryService(provider=MockDiscoveryProvider(seeded_sources=discovered))

    mock_fetcher = MagicMock(spec=SourceFetchService)
    mock_fetcher.fetch_all = AsyncMock(return_value=fetched)
    mock_fetcher.fetch_discovered_source = AsyncMock(return_value=fetched[0])

    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm,
        discovery_service=discovery_svc,
        fetch_service=mock_fetcher,
        extraction_service=EvidenceExtractionService(),
        validation_service=EvidenceValidationService(),
        calculation_service=CalculationService(),
    )

    req = PipelineRequest(
        business_idea="High-school online tutoring and test prep platform for students in India",
        target_geography="India",
        target_year=2024,
    )

    result = await pipeline.run(req)
    return "India high-school tutoring platform", result, raw_text


async def run_scenario_3():
    # Scenario 3: Tamil Nadu college food-delivery platform
    mock_llm = MagicMock(spec=OllamaLLMService)
    mock_llm.analyze_business_idea = AsyncMock(
        return_value=BusinessAnalysis(
            business_idea="Campus-focused meal and food delivery platform for college students in Tamil Nadu",
            product="College campus food delivery platform",
            industry="Food Delivery / Restaurant Tech",
            target_customer="College students",
            geography="Tamil Nadu",
            pricing_model="Per-order delivery fee",
            business_model="B2C Marketplace",
        )
    )
    mock_llm.generate_research_queries = AsyncMock(return_value=[
        ResearchQuery(metric_required="market size", industry_topic="Food Delivery", geography="Tamil Nadu", year=2024)
    ])

    raw_text = (
        "The total food delivery and meal service market in Tamil Nadu is valued at USD 420 million in 2024. "
        "Average student spends $12 per meal order on delivery platforms. "
        "Karnataka food delivery market was valued at $550 million in 2024. "
        "Online food delivery is projected to grow at a CAGR of 21.5% annually. "
        "Survey reveals 58% of college students prefer vegetarian food options. "
        "College campus and university student food delivery accounts for 22% of the food delivery market in Tamil Nadu. "
        "Summer promotions offer 20% off on all campus meal deliveries."
    )

    discovered = [
        DiscoveredSource(
            title="Tamil Nadu Food Delivery & College Food Service Study 2024",
            url="https://tnfoodstats.org/reports/food-delivery-tn-2024",
            snippet="Food delivery and restaurant market in Tamil Nadu reached USD 420 million in 2024. College campus food delivery accounts for 22% of total food delivery in Tamil Nadu.",
            mock_content=raw_text,
            source_name="TN Food & Beverage Association",
            category=SourceCategory.INDUSTRY_ANALYST,
            source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
            lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
            relevance_score=0.91,
        )
    ]

    fetched = [
        FetchedSource(
            original_url="https://tnfoodstats.org/reports/food-delivery-tn-2024",
            final_url="https://tnfoodstats.org/reports/food-delivery-tn-2024",
            title="Tamil Nadu Food Delivery & College Food Service Study 2024",
            raw_content=raw_text,
            extracted_text=raw_text,
            content=raw_text,
            fetch_status=FetchStatus.SUCCESS,
            status_code=200,
            content_length=len(raw_text),
            category=SourceCategory.INDUSTRY_ANALYST,
            source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
            lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
        )
    ]

    discovery_svc = DiscoveryService(provider=MockDiscoveryProvider(seeded_sources=discovered))

    mock_fetcher = MagicMock(spec=SourceFetchService)
    mock_fetcher.fetch_all = AsyncMock(return_value=fetched)
    mock_fetcher.fetch_discovered_source = AsyncMock(return_value=fetched[0])

    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm,
        discovery_service=discovery_svc,
        fetch_service=mock_fetcher,
        extraction_service=EvidenceExtractionService(),
        validation_service=EvidenceValidationService(),
        calculation_service=CalculationService(),
    )

    req = PipelineRequest(
        business_idea="Campus-focused meal and food delivery platform for college students in Tamil Nadu",
        target_geography="Tamil Nadu",
        target_year=2024,
    )

    result = await pipeline.run(req)
    return "Tamil Nadu college food-delivery platform", result, raw_text


async def main():
    scenarios = [await run_scenario_1(), await run_scenario_2(), await run_scenario_3()]
    for name, res, raw_text in scenarios:
        print("\n" + "="*90)
        print(f"DIAGNOSTIC REPORT: {name}")
        print("="*90)
        
        rep = res.calculation_report
        ext = res.extracted_candidates
        
        print("\n[EXTRACTED CANDIDATES]")
        for c in ext:
            print(f" - Metric: {c.metric} | Value: {c.value} {c.unit} | Type: {c.metric_type} | Geo: {c.geography} | Context: {c.source_context[:80]}...")
            
        print("\n[CALCULATION REPORT]")
        if rep:
            print(f"Overall Status: {rep.status}")
            print(f"Confidence: {rep.confidence}")
            if rep.top_down_tam:
                f = rep.top_down_tam.steps[0].formula if rep.top_down_tam.steps else "N/A"
                print(f"Top-Down TAM: Status={rep.top_down_tam.status} | Estimate={rep.top_down_tam.estimate} {rep.currency} | Interval={rep.top_down_tam.interval} | Formula={f}")
            if rep.top_down_sam:
                f = rep.top_down_sam.steps[0].formula if rep.top_down_sam.steps else "N/A"
                print(f"Top-Down SAM: Status={rep.top_down_sam.status} | Estimate={rep.top_down_sam.estimate} {rep.currency} | Interval={rep.top_down_sam.interval} | Formula={f} | Msg={rep.top_down_sam.message}")
            if rep.top_down_som:
                f = rep.top_down_som.steps[0].formula if rep.top_down_som.steps else "N/A"
                print(f"Top-Down SOM: Status={rep.top_down_som.status} | Estimate={rep.top_down_som.estimate} {rep.currency} | Interval={rep.top_down_som.interval} | Formula={f} | Msg={rep.top_down_som.message}")
            
            if rep.calculation_trace:
                tr = rep.calculation_trace
                print(f"\nTrace TAM: {tr.tam}")
                print(f"Trace SAM: {tr.sam}")
                print(f"Trace SOM: {tr.som}")
            
            print("\nWarnings:")
            for w in rep.warnings:
                print(f"  * {w}")
        else:
            print("No calculation report!")

if __name__ == "__main__":
    asyncio.run(main())
