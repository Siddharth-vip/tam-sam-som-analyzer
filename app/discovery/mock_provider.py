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
    """Deterministic in-memory discovery provider for testing and validation."""

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
        """Return matching seeded sources or a structured mock discovery result list."""
        query_string = self.build_query_string(query)
        logger.info("Executing mock discovery for query: '%s'", query_string)

        if self.seeded_sources is not None:
            return self.seeded_sources[: query.max_results]

        # Generate structured candidate search results for testing
        results: List[DiscoveredSource] = []
        
        geo_label = query.geography or "India"
        metric_req_lower = query.metric_required.lower()
        industry_lower = (query.industry_topic or "").lower()
        target_pop_lower = (query.target_population or "").lower()

        # Domain-aware mock content generation (prioritize specific industry sector)
        if "food" in industry_lower or "meal" in industry_lower or "restaurant" in industry_lower or "food" in metric_req_lower or "meal" in metric_req_lower:
            content_1 = f"Municipal and educational census data indicates {geo_label} has an active student and young adult population of 450,000 college students."
            snippet_1 = f"Urban Demographics Survey: 450,000 college students in {geo_label}."
            content_2 = f"The food delivery and meal subscription sector in {geo_label} generated USD 350 million in 2024. College students spend an average of INR 18,000 per year on meals and food delivery."
            snippet_2 = f"Food Services Study: USD 350 million market in {geo_label}; student meal spend INR 18,000/year."
            gov_domain = "chennaicorporation.gov.in" if "chennai" in geo_label.lower() else "statistics.gov.in"
            gov_source_name = "Department of Statistics and Consumer Studies"
        elif "saas" in industry_lower or "accounting" in industry_lower or "fintech" in industry_lower or "saas" in metric_req_lower or "accounting" in metric_req_lower:
            content_1 = f"According to official MSME statistical data, {geo_label} has approximately 63 million registered small businesses and micro-enterprises in 2024."
            snippet_1 = f"Ministry of MSME Report: 63 million small businesses in {geo_label}."
            content_2 = f"The cloud accounting and business software market in {geo_label} reached USD 1.2 billion in 2024. Small businesses spend an average annual price of INR 12,000 on SaaS accounting tools."
            snippet_2 = f"SaaS Benchmark Report: USD 1.2 billion market; annual software spend INR 12,000 per enterprise."
            gov_domain = "msme.gov.in"
            gov_source_name = "Ministry of Micro, Small and Medium Enterprises"
        elif "fitness" in industry_lower or "health" in industry_lower or "wellness" in industry_lower or "fitness" in metric_req_lower:
            content_1 = f"National health and wellness surveys estimate {geo_label} has 48 million urban working professionals actively participating in fitness activities."
            snippet_1 = f"Health Demographics Survey: 48 million working professionals in {geo_label}."
            content_2 = f"The digital fitness and wellness app market in {geo_label} was valued at USD 650 million in 2024. Users spend an average of INR 4,800 per year on fitness app subscriptions."
            snippet_2 = f"Fitness Market Study: USD 650 million market size in {geo_label}; annual subscription spend INR 4,800."
            gov_domain = "health.gov.in"
            gov_source_name = "National Health & Demographics Registry"
        elif "education" in industry_lower or "edtech" in industry_lower or "tutoring" in metric_req_lower or "student" in metric_req_lower or "student" in target_pop_lower:
            if "college" in metric_req_lower or "college" in target_pop_lower or "higher education" in metric_req_lower:
                content_1 = f"According to the official AISHE Higher Education Survey 2024, {geo_label} has approximately 41.3 million college students enrolled in higher education institutions."
                snippet_1 = f"Official AISHE Higher Education Survey: 41.3 million college students in {geo_label}."
                content_2 = f"The {geo_label} EdTech and online education market was valued at USD 2.5 billion in 2024. College students spend an average of INR 3,600 per year on online coding and skill courses."
                snippet_2 = f"EdTech Industry Study: Market valued at USD 2.5 billion in {geo_label}; average student spend is INR 3,600 per year."
            else:
                content_1 = f"According to national education statistics, {geo_label} has approximately 60 million high school and secondary students enrolled in 2024."
                snippet_1 = f"National Education Statistics: 60 million students in {geo_label}."
                content_2 = f"The online tutoring and test prep market in {geo_label} reached USD 1.8 billion in 2024 with an average annual spend of INR 4,500 per student."
                snippet_2 = f"Market Analysis: USD 1.8 billion tutoring market in {geo_label}; average annual spend INR 4,500."
            gov_domain = "aishe.gov.in"
            gov_source_name = "Ministry of Education / AISHE Report"
        else:
            content_1 = f"Official statistical report confirms target population for {query.metric_required} in {geo_label} is 25 million individuals in 2024."
            snippet_1 = f"Official Statistics: 25 million individuals in {geo_label}."
            content_2 = f"The market for {query.industry_topic or query.metric_required} in {geo_label} reached USD 1.0 billion in 2024 with an average annual spend of INR 5,000 per customer."
            snippet_2 = f"Market Study: USD 1.0 billion market in {geo_label}; average spend INR 5,000/year."
            gov_domain = "statistics.gov.in"
            gov_source_name = "National Statistical Commission"

        # Candidate 1: Official/Government candidate
        results.append(
            DiscoveredSource(
                title=f"{query.metric_required} - Official Statistical Report ({geo_label})",
                url=f"https://{gov_domain}/reports/{geo_label.lower()}-statistics",
                snippet=snippet_1,
                mock_content=content_1,
                source_name=gov_source_name,
                category=SourceCategory.OFFICIAL_GOVERNMENT,
                source_quality_tier=SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL,
                lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
                relevance_score=0.95,
                is_mock=True,
                query_used=query_string,
            )
        )

        # Candidate 2: Industry Analyst candidate
        results.append(
            DiscoveredSource(
                title=f"{query.industry_topic or query.metric_required} Annual Market & Industry Report",
                url=f"https://ibef.org/reports/{geo_label.lower()}-market-study",
                snippet=snippet_2,
                mock_content=content_2,
                source_name="India Brand Equity Foundation / Industry Analysts",
                category=SourceCategory.INDUSTRY_ANALYST,
                source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
                lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
                relevance_score=0.88,
                is_mock=True,
                query_used=query_string,
            )
        )

        return results[: query.max_results]
