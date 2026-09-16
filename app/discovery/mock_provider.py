import logging
from typing import List, Optional

from app.discovery.base import BaseDiscoveryProvider
from app.schemas.discovery import (
    DiscoveredSource,
    DiscoveryLifecycleStage,
    ResearchQuery,
    SourceCategory,
    SourceQualityTier,
)

logger = logging.getLogger(__name__)


class MockDiscoveryProvider(BaseDiscoveryProvider):
    """Deterministic in-memory discovery provider for Healthcare SaaS testing and validation."""

    def __init__(self, seeded_sources: Optional[List[DiscoveredSource]] = None) -> None:
        self.seeded_sources = seeded_sources

    def build_query_string(self, query: ResearchQuery) -> str:
        """Construct a standardized search query string."""
        parts = [query.metric_required.strip()]
        if query.target_population:
            parts.append(query.target_population.strip())
        if query.industry_topic:
            parts.append(query.industry_topic.strip())
        if query.geography:
            parts.append(query.geography.strip())
        if query.year:
            parts.append(str(query.year))
        return " ".join(parts)

    async def search(self, query: ResearchQuery) -> List[DiscoveredSource]:
        """Return matching seeded sources or structured Healthcare SaaS mock discovery results."""
        query_string = self.build_query_string(query)
        logger.info("Executing mock Healthcare SaaS discovery for query: '%s'", query_string)

        if self.seeded_sources is not None:
            return self.seeded_sources[: query.max_results]

        results: List[DiscoveredSource] = []
        geo_label = query.geography or "India"
        metric_req_lower = query.metric_required.lower()
        industry_lower = (query.industry_topic or "").lower()
        target_pop_lower = (query.target_population or "").lower()

        # Healthcare SaaS specific domain mock evidence
        if any(w in metric_req_lower or w in target_pop_lower for w in ["dental", "dentist", "oral care"]):
            content_1 = f"National Healthcare & Dental Council data confirms {geo_label} has approximately 35,000 registered dental clinics and practices in 2024."
            snippet_1 = f"Dental Registry Report: 35,000 dental clinics operating in {geo_label}."
            content_2 = f"The dental practice management and clinic SaaS market in {geo_label} reached USD 180 million in 2024. Dental clinics spend an average of INR 36,000 per year on practice software."
            snippet_2 = f"Healthcare SaaS Study: USD 180 million dental SaaS market in {geo_label}; average annual software spend is INR 36,000 per clinic."
            gov_domain = "mohfw.gov.in"
            gov_source_name = "Ministry of Health & Family Welfare / Dental Council"
        elif any(w in metric_req_lower or w in target_pop_lower for w in ["hospital", "hims", "his", "bed"]):
            content_1 = f"According to National Health Authority (NHA) healthcare infrastructure statistics, {geo_label} has approximately 69,000 registered hospitals (25,000 public and 44,000 private hospitals) in 2024."
            snippet_1 = f"National Health Registry: 69,000 registered hospitals in {geo_label}."
            content_2 = f"The hospital information management and EHR SaaS market in {geo_label} was valued at USD 1.4 billion in 2024. Hospitals spend an average annual subscription price of INR 2,40,000 on management software."
            snippet_2 = f"Hospital IT Survey: USD 1.4 billion market in {geo_label}; average hospital software spend is INR 2,40,000 per year."
            gov_domain = "nha.gov.in"
            gov_source_name = "National Health Authority / Ministry of Health"
        elif any(w in metric_req_lower or w in target_pop_lower for w in ["diagnostic", "pathology", "lab", "radiology", "imaging", "pacs"]):
            content_1 = f"National Health Mission & Diagnostic Industry Association reports confirm {geo_label} has approximately 100,000 diagnostic laboratories and pathology centers in 2024."
            snippet_1 = f"Diagnostic Infrastructure Report: 100,000 diagnostic laboratories in {geo_label}."
            content_2 = f"The diagnostic laboratory information system (LIMS) and PACS SaaS market in {geo_label} reached USD 420 million in 2024. Labs spend an average of INR 60,000 per year on SaaS tools."
            snippet_2 = f"Diagnostic SaaS Market: USD 420 million market in {geo_label}; annual spend INR 60,000 per lab."
            gov_domain = "mohfw.gov.in"
            gov_source_name = "National Health Mission / Ministry of Health"
        elif any(w in metric_req_lower or w in target_pop_lower for w in ["pharmacy", "pharmacies", "chemist", "drugstore"]):
            content_1 = f"Pharmacy Council of India statistics confirm {geo_label} has approximately 850,000 retail and hospital pharmacies operating in 2024."
            snippet_1 = f"Pharmacy Census: 850,000 pharmacies in {geo_label}."
            content_2 = f"The pharmacy management and e-prescription SaaS market in {geo_label} was valued at USD 310 million in 2024 with an average annual spend of INR 18,000 per pharmacy."
            snippet_2 = f"Pharmacy IT Analysis: USD 310 million market in {geo_label}; annual software spend INR 18,000."
            gov_domain = "pci.nic.in"
            gov_source_name = "Pharmacy Council of India"
        else:
            # General outpatient clinics / medical practices
            content_1 = f"According to Ministry of Health healthcare facility directory data, {geo_label} has approximately 150,000 outpatient clinics and private medical practices in 2024."
            snippet_1 = f"Official Healthcare Facilities Census: 150,000 outpatient clinics in {geo_label}."
            content_2 = f"The clinic management and healthcare SaaS market in {geo_label} was valued at USD 850 million in 2024. Outpatient clinics spend an average annual price of INR 48,000 on SaaS software."
            snippet_2 = f"Healthcare SaaS Industry Report: USD 850 million market in {geo_label}; average annual spend is INR 48,000 per clinic."
            gov_domain = "mohfw.gov.in"
            gov_source_name = "Ministry of Health and Family Welfare"

        # Candidate 1: Official/Government Tier 1 source
        results.append(
            DiscoveredSource(
                title=f"National Healthcare Infrastructure Census ({geo_label})",
                url=f"https://{gov_domain}/reports/{geo_label.lower()}-healthcare-infrastructure",
                snippet=snippet_1,
                mock_content=content_1,
                source_name=gov_source_name,
                domain=gov_domain,
                category=SourceCategory.OFFICIAL_GOVERNMENT.value,
                source_quality_tier=SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL.value,
                query_used=query_string,
                lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED.value,
                published_year=query.year or 2024,
                relevance_score=0.96,
                is_mock=True,
            )
        )

        # Candidate 2: Industry Analyst Tier 2 source
        analyst_domain = "grandviewresearch.com"
        results.append(
            DiscoveredSource(
                title=f"{query.metric_required} Healthcare SaaS Market Report 2024-2030",
                url=f"https://{analyst_domain}/industry-analysis/{geo_label.lower()}-healthcare-saas",
                snippet=snippet_2,
                mock_content=content_2,
                source_name="Grand View Healthcare IT Intelligence",
                domain=analyst_domain,
                category=SourceCategory.INDUSTRY_ANALYST.value,
                source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE.value,
                query_used=query_string,
                lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED.value,
                published_year=query.year or 2024,
                relevance_score=0.91,
                is_mock=True,
            )
        )

        return results[: query.max_results]
