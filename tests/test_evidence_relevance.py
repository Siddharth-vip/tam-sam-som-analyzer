import pytest
from app.schemas.business import BusinessAnalysis, HealthcareCustomerType, HealthcareSaaSCategory
from app.schemas.discovery import DiscoveryLifecycleStage, SourceQualityTier
from app.schemas.extraction import ExtractedEvidenceCandidate, ExtractionMethod
from app.schemas.validation import (
    EvidenceValidationStatus,
    MarketDefinitionCompatibility,
    SuitabilityRating,
)
from app.services.validation_service import EvidenceValidationService


@pytest.fixture
def clinic_business_analysis():
    return BusinessAnalysis(
        business_name="ClinicaFlow",
        business_idea="Cloud-based clinic management SaaS for small and medium-sized clinics in India.",
        industry="Healthcare Information Technology",
        healthcare_saas_category=HealthcareSaaSCategory.CLINIC_MANAGEMENT,
        customer_type=HealthcareCustomerType.CLINICS,
        target_customer="Small and medium-sized private clinics",
        target_country="India",
        geography="India",
        product="Cloud-based clinic management SaaS for small and medium clinics in India",
        business_model="B2B SaaS",
        pricing_basis="per_facility",
    )


@pytest.fixture
def validation_service():
    return EvidenceValidationService()


# 1. Directly relevant clinic source
def test_1_directly_relevant_clinic_source(validation_service, clinic_business_analysis):
    candidate = ExtractedEvidenceCandidate(
        metric="registered outpatient clinics in India",
        value=150000.0,
        unit="clinics",
        geography="India",
        year=2024,
        source_url="https://mohfw.gov.in/reports/india-healthcare-census",
        source_name="Ministry of Health and Family Welfare",
        source_context="According to Ministry of Health data, India has approximately 150,000 outpatient clinics and private practices in 2024.",
        extraction_method=ExtractionMethod.DETERMINISTIC_PATTERN,
    )
    result = validation_service.validate_candidate(candidate, business_analysis=clinic_business_analysis)
    
    assert result.is_valid is True
    assert result.evidence_suitability is not None
    assert result.evidence_suitability.geographic_match is True
    assert result.evidence_suitability.customer_type_match is True
    assert result.evidence_suitability.definition_compatibility == MarketDefinitionCompatibility.DIRECT_MATCH
    assert result.evidence_suitability.overall == SuitabilityRating.HIGH


# 2. Broad parent healthcare market source
def test_2_broad_parent_healthcare_source(validation_service, clinic_business_analysis):
    candidate = ExtractedEvidenceCandidate(
        metric="total healthcare IT market size",
        value=5000000000.0,
        unit="USD",
        geography="India",
        year=2024,
        source_url="https://www.grandviewresearch.com/industry-analysis/india-healthcare-it-market",
        source_name="Grand View Research",
        source_context="The overall India healthcare IT and software market was valued at USD 5.0 billion in 2024.",
        extraction_method=ExtractionMethod.DETERMINISTIC_PATTERN,
    )
    result = validation_service.validate_candidate(candidate, business_analysis=clinic_business_analysis)
    
    assert result.is_valid is True
    assert result.evidence_suitability.definition_compatibility == MarketDefinitionCompatibility.BROAD_PARENT_MARKET
    assert result.evidence_suitability.overall == SuitabilityRating.LOW
    assert "Broad parent market" in result.evidence_suitability.reason


# 3. Related Revenue Cycle Management (RCM) source
def test_3_related_rcm_source_for_clinic_saas(validation_service, clinic_business_analysis):
    candidate = ExtractedEvidenceCandidate(
        metric="empanelled hospitals and healthcare practices",
        value=32574.0,
        unit="facilities",
        geography="India",
        year=2025,
        source_url="https://www.kenresearch.com/industry-reports/india-revenue-cycle-management-market",
        source_name="Ken Research",
        source_context="The India Revenue Cycle Management market covers 32,574 empanelled hospitals and healthcare practices in 2025.",
        extraction_method=ExtractionMethod.DETERMINISTIC_PATTERN,
    )
    result = validation_service.validate_candidate(candidate, business_analysis=clinic_business_analysis)
    
    assert result.is_valid is True
    assert result.evidence_suitability.definition_compatibility == MarketDefinitionCompatibility.RELATED_MARKET
    assert result.evidence_suitability.customer_type_match is False
    assert result.evidence_suitability.overall == SuitabilityRating.LOW
    assert "Revenue Cycle Management" in result.evidence_suitability.reason


# 4. Unrelated domain source (e.g. Pet care or meal delivery)
def test_4_unrelated_domain_source(validation_service, clinic_business_analysis):
    candidate = ExtractedEvidenceCandidate(
        metric="pet care centers in India",
        value=12000.0,
        unit="centers",
        geography="India",
        year=2024,
        source_url="https://www.petindustry.com/india-pet-care",
        source_name="Pet Industry Report",
        source_context="India has over 12,000 pet care and veterinary centers in 2024.",
        extraction_method=ExtractionMethod.DETERMINISTIC_PATTERN,
    )
    result = validation_service.validate_candidate(candidate, business_analysis=clinic_business_analysis)
    
    assert result.evidence_suitability.definition_compatibility == MarketDefinitionCompatibility.UNRELATED
    assert result.evidence_suitability.overall == SuitabilityRating.UNSUITABLE
    assert "Unrelated domain" in result.evidence_suitability.reason


# 5. Wrong geography mismatch
def test_5_wrong_geography_mismatch(validation_service, clinic_business_analysis):
    candidate = ExtractedEvidenceCandidate(
        metric="outpatient clinics in United States",
        value=240000.0,
        unit="clinics",
        geography="United States",
        year=2024,
        source_url="https://www.cdc.gov/nchs/fastats/clinics.htm",
        source_name="CDC National Center for Health Statistics",
        source_context="In the United States, there are 240,000 ambulatory medical clinics in 2024.",
        extraction_method=ExtractionMethod.DETERMINISTIC_PATTERN,
    )
    result = validation_service.validate_candidate(candidate, business_analysis=clinic_business_analysis)
    
    assert result.evidence_suitability.geographic_match is False
    assert result.evidence_suitability.overall == SuitabilityRating.UNSUITABLE
    assert "Geographic mismatch" in result.evidence_suitability.reason


# 6. Wrong customer type (Hospital beds for a Clinic SaaS)
def test_6_wrong_customer_type(validation_service, clinic_business_analysis):
    candidate = ExtractedEvidenceCandidate(
        metric="registered tertiary hospitals in India",
        value=69000.0,
        unit="hospitals",
        geography="India",
        year=2024,
        source_url="https://www.nha.gov.in/hospital-census",
        source_name="National Health Authority",
        source_context="India has approximately 69,000 operational private and government hospitals in 2024.",
        extraction_method=ExtractionMethod.DETERMINISTIC_PATTERN,
    )
    result = validation_service.validate_candidate(candidate, business_analysis=clinic_business_analysis)
    
    assert result.evidence_suitability.customer_type_match is False
    assert result.evidence_suitability.overall in (SuitabilityRating.LOW, SuitabilityRating.MEDIUM)


# 7. Outdated source (temporal mismatch)
def test_7_outdated_source_temporal_caveat(validation_service, clinic_business_analysis):
    candidate = ExtractedEvidenceCandidate(
        metric="clinics in India",
        value=85000.0,
        unit="clinics",
        geography="India",
        year=2014,
        source_url="https://mohfw.gov.in/archive/2014-report",
        source_name="MoHFW Archive",
        source_context="Directory statistics in 2014 showed 85,000 registered clinics.",
        extraction_method=ExtractionMethod.DETERMINISTIC_PATTERN,
    )
    result = validation_service.validate_candidate(candidate, business_analysis=clinic_business_analysis)
    
    assert result.evidence_suitability.temporal_match is False
    assert "Temporal caveat" in result.evidence_suitability.reason


# 8. Incompatible populations are not blended together
def test_8_incompatible_populations_triangulation(validation_service, clinic_business_analysis):
    cand_clinics = ExtractedEvidenceCandidate(
        metric="outpatient clinics in India",
        value=150000.0,
        unit="clinics",
        geography="India",
        year=2024,
        source_url="https://mohfw.gov.in/census",
        source_name="MoHFW",
        source_context="150,000 outpatient clinics operating in India in 2024.",
    )
    cand_hospitals = ExtractedEvidenceCandidate(
        metric="empanelled hospitals in India",
        value=32574.0,
        unit="hospitals",
        geography="India",
        year=2025,
        source_url="https://kenresearch.com/rcm",
        source_name="Ken Research",
        source_context="32,574 empanelled hospitals operating in India in 2025.",
    )
    
    tri_res = validation_service.triangulate_evidence([cand_clinics, cand_hospitals], business_analysis=clinic_business_analysis)
    
    # Verify each maintains distinct validated identity without being averaged
    vals = [item.value for item in tri_res.validated_items]
    assert 150000.0 in vals
    assert 32574.0 in vals
    assert len(tri_res.validated_items) == 2


# 9. Valid multi-source triangulation corroboration
def test_9_valid_triangulation_corroboration(validation_service, clinic_business_analysis):
    cand_src_1 = ExtractedEvidenceCandidate(
        metric="outpatient clinics in India",
        value=150000.0,
        unit="clinics",
        geography="India",
        year=2024,
        source_url="https://mohfw.gov.in/census-1",
        source_name="Ministry of Health",
        source_context="India has approximately 150,000 outpatient clinics in 2024.",
    )
    cand_src_2 = ExtractedEvidenceCandidate(
        metric="outpatient clinics in India",
        value=150000.0,
        unit="clinics",
        geography="India",
        year=2024,
        source_url="https://nha.gov.in/census-2",
        source_name="National Health Authority",
        source_context="National directory records 150,000 outpatient medical clinics in India.",
    )
    
    tri_res = validation_service.triangulate_evidence([cand_src_1, cand_src_2], business_analysis=clinic_business_analysis)
    
    assert len(tri_res.verified_items) == 1
    assert tri_res.verified_items[0].corroborating_source_count >= 2
    assert tri_res.verified_items[0].lifecycle_stage == DiscoveryLifecycleStage.VERIFIED.value


# 10. Live source provenance preservation
def test_10_live_source_provenance_preserved(validation_service, clinic_business_analysis):
    candidate = ExtractedEvidenceCandidate(
        metric="clinic management SaaS subscription price in India",
        value=48000.0,
        unit="INR/year",
        geography="India",
        year=2025,
        source_url="https://www.nzcares.com/blogs/clinic-management-software-india-pricing-guide",
        source_name="NZ Cares Healthcare Guide",
        source_context="Clinic management software in India costs an average annual price of INR 48,000 per facility.",
    )
    result = validation_service.validate_candidate(candidate, business_analysis=clinic_business_analysis)
    
    assert result.source_url == "https://www.nzcares.com/blogs/clinic-management-software-india-pricing-guide"
    assert result.source_name == "NZ Cares Healthcare Guide"
    assert result.evidence_suitability.definition_compatibility == MarketDefinitionCompatibility.DIRECT_MATCH
    assert result.evidence_suitability.overall == SuitabilityRating.HIGH


# 11. Insufficient evidence handling
def test_11_insufficient_evidence_handling(validation_service, clinic_business_analysis):
    # Pass empty candidates list
    tri_res = validation_service.triangulate_evidence([], business_analysis=clinic_business_analysis)
    assert len(tri_res.validated_items) == 0
    assert len(tri_res.verified_items) == 0


# 12. Mock source provenance classification
def test_12_mock_source_provenance_classification(validation_service, clinic_business_analysis):
    from app.discovery.mock_provider import MockDiscoveryProvider
    from app.schemas.discovery import ResearchQuery
    import asyncio
    
    mock_prov = MockDiscoveryProvider()
    q = ResearchQuery(metric_required="clinics in India", geography="India", year=2024)
    sources = asyncio.run(mock_prov.search(q))
    
    assert len(sources) >= 1
    assert sources[0].is_mock is True
    assert "mohfw.gov.in" in sources[0].url
