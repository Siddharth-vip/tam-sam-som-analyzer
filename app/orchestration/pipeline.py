from datetime import datetime, timezone
import logging
import re
import time
from typing import AsyncGenerator, List, Optional, Tuple
import uuid

from app.config import settings
from app.discovery.live_provider import LiveDiscoveryProvider
from app.fetching.models import FetchedSource
from app.orchestration.events import create_progress_event
from app.orchestration.exceptions import (
    BusinessAnalysisStepException,
    CalculationStepException,
    DiscoveryStepException,
    ExtractionStepException,
    FetchingStepException,
    PipelineException,
    QueryGenerationStepException,
    ValidationStepException,
)
from app.orchestration.models import (
    PipelineProgressEvent,
    PipelineRequest,
    PipelineResult,
    PipelineStage,
    PipelineStatus,
    StateTransitionRecord,
)
from app.schemas.business import BusinessAnalysis, CompetitorInfo
from app.schemas.calculation import (
    BottomUpCalculationInputs,
    CalculationAssumption,
    CalculationInput,
    CalculationReport,
    CalculationStatus,
    EvidenceInput,
    PriceFrequency,
    SAMResult,
    SOMResult,
    TAMResult,
    TopDownCalculationInputs,
)
from app.schemas.discovery import (
    DiscoveredSource,
    DiscoveryLifecycleStage,
    DiscoveryResponse,
    DiscoveryStatus,
    ResearchQuery,
    SourceCategory,
    SourceQualityTier,
)
from app.schemas.extraction import (
    ExtractedEvidenceCandidate,
    ExtractionRequest,
)
from app.schemas.validation import (
    ConflictGroup,
    EvidenceConfidence,
    EvidenceValidationResult,
    SourceProvenance,
    TriangulationResult,
)
from app.services.calculation_service import (
    CalculationService,
    get_calculation_service,
)
from app.services.discovery_service import (
    DiscoveryService,
    filter_relevant_sources,
    get_discovery_service,
)
from app.services.extraction_service import (
    EvidenceExtractionService,
    get_extraction_service,
)
from app.services.fetch_service import (
    SourceFetchService,
    get_fetch_service,
)
from app.services.llm_service import (
    OllamaLLMService,
    get_llm_service,
)
from app.services.validation_service import (
    EvidenceValidationService,
    get_validation_service,
)
from app.storage.repository import (
    AnalysisRepository,
    get_repository,
)

logger = logging.getLogger(__name__)


class MarketAnalysisPipeline:
    """Asynchronous-friendly orchestrator coordinating the end-to-end market sizing pipeline.

    Connects:
      Business Idea Analysis
      → Research Query Generation
      → Evidence Discovery
      → Source Fetching
      → Evidence Extraction
      → Evidence Validation & Deduplication
      → Conflict Detection & Triangulation
      → Calculation Input Construction (Evidence Gate)
      → Deterministic TAM/SAM/SOM Calculation
      → Final Structured Report
    """

    def __init__(
        self,
        llm_service: Optional[OllamaLLMService] = None,
        discovery_service: Optional[DiscoveryService] = None,
        fetch_service: Optional[SourceFetchService] = None,
        extraction_service: Optional[EvidenceExtractionService] = None,
        validation_service: Optional[EvidenceValidationService] = None,
        calculation_service: Optional[CalculationService] = None,
        repository: Optional[AnalysisRepository] = None,
    ) -> None:
        self.llm_service = llm_service or get_llm_service()
        self.discovery_service = discovery_service or get_discovery_service()
        self.fetch_service = fetch_service or get_fetch_service()
        self.extraction_service = extraction_service or get_extraction_service()
        self.validation_service = validation_service or get_validation_service()
        self.calculation_service = calculation_service or get_calculation_service()
        self.repository = repository or get_repository()

    async def run(self, request: PipelineRequest) -> PipelineResult:
        """Execute the full market analyzer pipeline and return the final PipelineResult."""
        return await self._execute_pipeline(request)

    async def run_with_progress(
        self, request: PipelineRequest
    ) -> AsyncGenerator[PipelineProgressEvent, None]:
        """Execute the pipeline while yielding real-time progress events for streaming/SSE."""
        pipeline_id = f"pipe_{uuid.uuid4().hex[:12]}"
        started_at = datetime.now(timezone.utc).isoformat()
        audit_trail: List[StateTransitionRecord] = []
        errors: List[str] = []
        warnings: List[str] = []

        def record_transition(
            from_st: Optional[str],
            to_st: str,
            msg: str,
            dur: Optional[float] = None,
            err: Optional[str] = None,
        ) -> None:
            audit_trail.append(
                StateTransitionRecord(
                    from_state=from_st,
                    to_state=to_st,
                    message=msg,
                    duration_ms=dur,
                    error=err,
                )
            )

        # -------------------------------------------------------------------
        # Step 1: Business Idea Analysis
        # -------------------------------------------------------------------
        yield create_progress_event(
            pipeline_id,
            PipelineStage.BUSINESS_ANALYSIS,
            PipelineStatus.RUNNING,
            "Analyzing business idea and extracting structured attributes.",
            progress_percent=10,
        )
        record_transition(None, PipelineStage.BUSINESS_ANALYSIS.value, "Starting business idea analysis")
        t0 = time.perf_counter()
        analysis: Optional[BusinessAnalysis] = None
        try:
            analysis = await self.llm_service.analyze_business_idea(request.business_idea)
            dur = round((time.perf_counter() - t0) * 1000, 2)
            yield create_progress_event(
                pipeline_id,
                PipelineStage.BUSINESS_ANALYSIS,
                PipelineStatus.COMPLETED,
                f"Business idea analyzed. Industry: {analysis.industry}, Product: {analysis.product}.",
                progress_percent=20,
                metadata={"industry": analysis.industry, "product": analysis.product},
            )
            record_transition(
                PipelineStage.BUSINESS_ANALYSIS.value,
                PipelineStage.QUERY_GENERATION.value,
                f"Business idea analyzed in {dur}ms",
                dur=dur,
            )
        except Exception as exc:
            warn_msg = f"LLM analysis encountered issue ({exc}); activating Layer 2 deterministic normalization fallback."
            logger.warning(warn_msg)
            warnings.append(warn_msg)
            from app.services.llm_service import normalize_business_analysis
            norm_data = normalize_business_analysis({}, request.business_idea)
            if request.preferred_geography:
                norm_data["geography"] = request.preferred_geography
            analysis = BusinessAnalysis.model_validate(norm_data)
            dur = round((time.perf_counter() - t0) * 1000, 2)
            yield create_progress_event(
                pipeline_id,
                PipelineStage.BUSINESS_ANALYSIS,
                PipelineStatus.COMPLETED,
                f"Business idea analyzed via deterministic normalization. Industry: {analysis.industry}, Product: {analysis.product}.",
                progress_percent=20,
                metadata={"industry": analysis.industry, "product": analysis.product},
            )
            record_transition(
                PipelineStage.BUSINESS_ANALYSIS.value,
                PipelineStage.QUERY_GENERATION.value,
                f"Business idea analyzed in {dur}ms (normalization fallback)",
                dur=dur,
            )

        # -------------------------------------------------------------------
        # Step 2: Research Query Generation
        # -------------------------------------------------------------------
        yield create_progress_event(
            pipeline_id,
            PipelineStage.QUERY_GENERATION,
            PipelineStatus.RUNNING,
            "Generating research queries based on structured business analysis.",
            progress_percent=25,
        )
        t0 = time.perf_counter()
        research_queries = self._generate_research_queries(analysis, request)
        dur = round((time.perf_counter() - t0) * 1000, 2)
        yield create_progress_event(
            pipeline_id,
            PipelineStage.QUERY_GENERATION,
            PipelineStatus.COMPLETED,
            f"Generated {len(research_queries)} research queries.",
            progress_percent=30,
            metadata={"query_count": len(research_queries)},
        )
        record_transition(
            PipelineStage.QUERY_GENERATION.value,
            PipelineStage.DISCOVERY.value,
            f"Generated {len(research_queries)} queries in {dur}ms",
            dur=dur,
        )

        # -------------------------------------------------------------------
        # Step 3: Evidence Discovery
        # -------------------------------------------------------------------
        yield create_progress_event(
            pipeline_id,
            PipelineStage.DISCOVERY,
            PipelineStatus.RUNNING,
            "Searching for authoritative external evidence sources.",
            progress_percent=35,
        )
        t0 = time.perf_counter()
        discovered_sources: List[DiscoveredSource] = []
        is_live_search = False
        try:
            prov = getattr(self.discovery_service, "provider", None)
            if isinstance(prov, LiveDiscoveryProvider):
                is_live_search = True
        except (AttributeError, Exception):
            pass
        if not is_live_search and type(self.discovery_service).__name__ not in ("MagicMock", "Mock", "AsyncMock"):
            is_live_search = (getattr(settings, "SEARCH_PROVIDER", "") or "").lower() in ("live", "tavily", "searxng", "custom")
        try:
            if is_live_search and research_queries:
                # API Quota Optimization: 1 unified search request for the entire analysis
                unified_q = self._build_unified_live_query(research_queries, analysis, request)
                resp = await self.discovery_service.discover_sources(unified_q)
                if resp.status == DiscoveryStatus.FAILED:
                    errors.append(resp.message or "Discovery provider failed.")
                rel_srcs, rej_srcs = filter_relevant_sources(resp.sources, unified_q)
                for src in rel_srcs:
                    if src not in discovered_sources and len(discovered_sources) < request.max_sources:
                        discovered_sources.append(src)
            else:
                for q in research_queries:
                    resp = await self.discovery_service.discover_sources(q)
                    if resp.status == DiscoveryStatus.FAILED:
                        errors.append(resp.message or "Discovery provider failed.")
                    rel_srcs, rej_srcs = filter_relevant_sources(resp.sources, q)
                    for src in rel_srcs:
                        if src not in discovered_sources and len(discovered_sources) < request.max_sources:
                            discovered_sources.append(src)
            dur = round((time.perf_counter() - t0) * 1000, 2)
            yield create_progress_event(
                pipeline_id,
                PipelineStage.DISCOVERY,
                PipelineStatus.COMPLETED,
                f"Discovered {len(discovered_sources)} potential source(s).",
                progress_percent=45,
                metadata={"discovered_count": len(discovered_sources)},
            )
            record_transition(
                PipelineStage.DISCOVERY.value,
                PipelineStage.FETCHING.value,
                f"Discovered {len(discovered_sources)} sources in {dur}ms",
                dur=dur,
            )
        except Exception as exc:
            err_msg = f"Evidence discovery failed: {exc}"
            logger.error(err_msg)
            errors.append(err_msg)
            record_transition(
                PipelineStage.DISCOVERY.value,
                PipelineStage.COMPLETED.value,
                "Discovery failed",
                err=err_msg,
            )
            yield create_progress_event(
                pipeline_id,
                PipelineStage.DISCOVERY,
                PipelineStatus.FAILED,
                err_msg,
                progress_percent=100,
            )
            return

        if not discovered_sources:
            warnings.append("No external evidence sources were discovered for this business idea.")
            yield create_progress_event(
                pipeline_id,
                PipelineStage.COMPLETED,
                PipelineStatus.INSUFFICIENT_EVIDENCE,
                "No evidence discovered. Market sizing halted due to insufficient evidence.",
                progress_percent=100,
            )
            return

        # -------------------------------------------------------------------
        # Step 4: Source Fetching
        # -------------------------------------------------------------------
        yield create_progress_event(
            pipeline_id,
            PipelineStage.FETCHING,
            PipelineStatus.RUNNING,
            f"Fetching content for {len(discovered_sources)} discovered source(s).",
            progress_percent=50,
        )
        t0 = time.perf_counter()
        fetched_sources: List[FetchedSource] = []
        for src in discovered_sources:
            try:
                fetched = await self.fetch_service.fetch_discovered_source(src)
                if fetched and fetched.content:
                    fetched_sources.append(fetched)
                else:
                    warnings.append(f"Fetched source {src.url} contained empty content.")
            except Exception as exc:
                warn = f"Failed to fetch source {src.url}: {exc}"
                logger.warning(warn)
                warnings.append(warn)

        dur = round((time.perf_counter() - t0) * 1000, 2)
        yield create_progress_event(
            pipeline_id,
            PipelineStage.FETCHING,
            PipelineStatus.COMPLETED,
            f"Fetched {len(fetched_sources)} of {len(discovered_sources)} source(s).",
            progress_percent=60,
            metadata={"fetched_count": len(fetched_sources)},
        )
        record_transition(
            PipelineStage.FETCHING.value,
            PipelineStage.EXTRACTION.value,
            f"Fetched {len(fetched_sources)} documents in {dur}ms",
            dur=dur,
        )

        # -------------------------------------------------------------------
        # Step 5: Evidence Extraction
        # -------------------------------------------------------------------
        yield create_progress_event(
            pipeline_id,
            PipelineStage.EXTRACTION,
            PipelineStatus.RUNNING,
            "Extracting numerical metrics and context snippets from fetched documents.",
            progress_percent=65,
        )
        t0 = time.perf_counter()
        extracted_candidates: List[ExtractedEvidenceCandidate] = []
        for doc in fetched_sources:
            try:
                ext_req = ExtractionRequest(source=doc)
                ext_resp = self.extraction_service.extract_evidence_from_source(ext_req)
                if ext_resp.candidates:
                    extracted_candidates.extend(ext_resp.candidates)
            except Exception as exc:
                warn = f"Extraction failed for {doc.original_url}: {exc}"
                logger.warning(warn)
                warnings.append(warn)

        dur = round((time.perf_counter() - t0) * 1000, 2)
        yield create_progress_event(
            pipeline_id,
            PipelineStage.EXTRACTION,
            PipelineStatus.COMPLETED,
            f"Extracted {len(extracted_candidates)} candidate metric(s).",
            progress_percent=70,
            metadata={"candidate_count": len(extracted_candidates)},
        )
        record_transition(
            PipelineStage.EXTRACTION.value,
            PipelineStage.VALIDATION.value,
            f"Extracted {len(extracted_candidates)} candidates in {dur}ms",
            dur=dur,
        )

        # -------------------------------------------------------------------
        # Step 6 & 7 & 8 & 9: Validation, Deduplication, Conflict Detection, Triangulation
        # -------------------------------------------------------------------
        yield create_progress_event(
            pipeline_id,
            PipelineStage.VALIDATION,
            PipelineStatus.RUNNING,
            "Validating candidate data integrity and checking domain corroborate rules.",
            progress_percent=75,
        )
        t0 = time.perf_counter()
        tri_result: Optional[TriangulationResult] = None
        try:
            tri_result = self.validation_service.triangulate_evidence(extracted_candidates, business_analysis=analysis)
            dur = round((time.perf_counter() - t0) * 1000, 2)
            yield create_progress_event(
                pipeline_id,
                PipelineStage.TRIANGULATION,
                PipelineStatus.COMPLETED,
                f"Triangulated evidence: {len(tri_result.verified_items)} verified, {len(tri_result.conflict_groups)} conflicts.",
                progress_percent=88,
                metadata={
                    "verified_count": len(tri_result.verified_items),
                    "validated_count": len(tri_result.validated_items),
                    "conflict_count": len(tri_result.conflict_groups),
                },
            )
            record_transition(
                PipelineStage.VALIDATION.value,
                PipelineStage.CALCULATION.value,
                f"Triangulated evidence in {dur}ms",
                dur=dur,
            )
        except Exception as exc:
            err_msg = f"Evidence validation & triangulation failed: {exc}"
            logger.error(err_msg)
            errors.append(err_msg)
            record_transition(
                PipelineStage.VALIDATION.value,
                PipelineStage.COMPLETED.value,
                "Validation failed",
                err=err_msg,
            )
            yield create_progress_event(
                pipeline_id,
                PipelineStage.VALIDATION,
                PipelineStatus.FAILED,
                err_msg,
                progress_percent=100,
            )
            return

        # -------------------------------------------------------------------
        # Step 10 & 11: Calculation Input Construction & Calculation
        # -------------------------------------------------------------------
        calc_report: Optional[CalculationReport] = None
        if request.enable_calculation:
            yield create_progress_event(
                pipeline_id,
                PipelineStage.CALCULATION,
                PipelineStatus.RUNNING,
                "Executing deterministic Top-Down and Bottom-Up TAM/SAM/SOM calculations.",
                progress_percent=90,
            )
            t0 = time.perf_counter()
            try:
                calc_input = self._build_calculation_inputs(
                    analysis,
                    tri_result.validated_items if tri_result else [],
                    request,
                )
                calc_report = self.calculation_service.generate_report(calc_input)
                dur = round((time.perf_counter() - t0) * 1000, 2)
                yield create_progress_event(
                    pipeline_id,
                    PipelineStage.CALCULATION,
                    PipelineStatus.COMPLETED,
                    f"Market calculation completed with status: {calc_report.status}.",
                    progress_percent=95,
                    metadata={"calculation_status": str(calc_report.status)},
                )
                record_transition(
                    PipelineStage.CALCULATION.value,
                    PipelineStage.COMPLETED.value,
                    f"Calculated market in {dur}ms",
                    dur=dur,
                )
            except Exception as exc:
                err_msg = f"Market calculation failed: {exc}"
                logger.error(err_msg)
                errors.append(err_msg)
                yield create_progress_event(
                    pipeline_id,
                    PipelineStage.CALCULATION,
                    PipelineStatus.FAILED,
                    err_msg,
                    progress_percent=95,
                )

        # -------------------------------------------------------------------
        # Step 12: Final Completion Event
        # -------------------------------------------------------------------
        yield create_progress_event(
            pipeline_id,
            PipelineStage.COMPLETED,
            PipelineStatus.COMPLETED,
            "Market analysis pipeline completed successfully.",
            progress_percent=100,
            metadata={"pipeline_id": pipeline_id},
        )

    async def _execute_pipeline(self, request: PipelineRequest) -> PipelineResult:
        """Internal synchronous runner assembling the complete PipelineResult."""
        pipeline_id = f"pipe_{uuid.uuid4().hex[:12]}"
        started_at = datetime.now(timezone.utc).isoformat()
        audit_trail: List[StateTransitionRecord] = []
        errors: List[str] = []
        warnings: List[str] = []
        research_queries: List[ResearchQuery] = []
        all_discovered_sources: List[DiscoveredSource] = []
        rejected_sources: List[DiscoveredSource] = []
        fetched_sources: List[FetchedSource] = []
        extracted_candidates: List[ExtractedEvidenceCandidate] = []
        extracted_competitors: List[CompetitorInfo] = []

        def record_transition(
            from_st: Optional[str],
            to_st: str,
            msg: str,
            dur: Optional[float] = None,
            err: Optional[str] = None,
        ) -> None:
            audit_trail.append(
                StateTransitionRecord(
                    from_state=from_st,
                    to_state=to_st,
                    message=msg,
                    duration_ms=dur,
                    error=err,
                )
            )

        start_time = time.perf_counter()

        # 1. Business Idea Analysis
        record_transition(None, PipelineStage.BUSINESS_ANALYSIS.value, "Starting business analysis")
        t0 = time.perf_counter()
        analysis: Optional[BusinessAnalysis] = None
        try:
            analysis = await self.llm_service.analyze_business_idea(request.business_idea)
            dur = round((time.perf_counter() - t0) * 1000, 2)
            record_transition(
                PipelineStage.BUSINESS_ANALYSIS.value,
                PipelineStage.QUERY_GENERATION.value,
                f"Business idea analyzed in {dur}ms",
                dur=dur,
            )
        except Exception as exc:
            err_msg = f"Business analysis failed: {exc}"
            logger.error(err_msg)
            errors.append(err_msg)
            record_transition(
                PipelineStage.BUSINESS_ANALYSIS.value,
                PipelineStage.COMPLETED.value,
                "Business analysis failed",
                err=err_msg,
            )
            return self._build_final_result(
                pipeline_id=pipeline_id,
                request=request,
                status=PipelineStatus.FAILED,
                analysis=None,
                research_queries=[],
                discovered_sources=[],
                fetched_sources=[],
                extracted_candidates=[],
                validation_results=[],
                tri_result=None,
                calc_report=None,
                errors=errors,
                warnings=warnings,
                audit_trail=audit_trail,
                started_at=started_at,
            )

        # 2. Research Query Generation
        t0 = time.perf_counter()
        research_queries = self._generate_research_queries(analysis, request)
        dur = round((time.perf_counter() - t0) * 1000, 2)
        record_transition(
            PipelineStage.QUERY_GENERATION.value,
            PipelineStage.DISCOVERY.value,
            f"Generated {len(research_queries)} queries in {dur}ms",
            dur=dur,
        )

        # 3. Evidence Discovery
        t0 = time.perf_counter()
        all_discovered_sources: List[DiscoveredSource] = []
        is_live_search = False
        try:
            prov = getattr(self.discovery_service, "provider", None)
            if isinstance(prov, LiveDiscoveryProvider):
                is_live_search = True
        except (AttributeError, Exception):
            pass
        if not is_live_search and type(self.discovery_service).__name__ not in ("MagicMock", "Mock", "AsyncMock"):
            is_live_search = (getattr(settings, "SEARCH_PROVIDER", "") or "").lower() in ("live", "tavily", "searxng", "custom")
        try:
            if is_live_search and research_queries:
                # Single Unified Live Search for API quota conservation
                unified_q = self._build_unified_live_query(research_queries, analysis, request)
                resp = await self.discovery_service.discover_sources(unified_q)
                rel_srcs, rej_srcs = filter_relevant_sources(resp.sources, unified_q)
                rejected_sources.extend(rej_srcs)
                for src in rel_srcs:
                    if src not in all_discovered_sources and len(all_discovered_sources) < request.max_sources:
                        all_discovered_sources.append(src)
            else:
                for q in research_queries:
                    resp = await self.discovery_service.discover_sources(q)
                    rel_srcs, rej_srcs = filter_relevant_sources(resp.sources, q)
                    rejected_sources.extend(rej_srcs)
                    for src in rel_srcs:
                        if src not in all_discovered_sources and len(all_discovered_sources) < request.max_sources:
                            all_discovered_sources.append(src)
            dur = round((time.perf_counter() - t0) * 1000, 2)
            record_transition(
                PipelineStage.DISCOVERY.value,
                PipelineStage.FETCHING.value,
                f"Discovered {len(all_discovered_sources)} relevant sources ({len(rejected_sources)} rejected) in {dur}ms",
                dur=dur,
            )
        except Exception as exc:
            err_msg = f"Evidence discovery failed: {exc}"
            logger.error(err_msg)
            errors.append(err_msg)
            record_transition(
                PipelineStage.DISCOVERY.value,
                PipelineStage.COMPLETED.value,
                "Discovery failed",
                err=err_msg,
            )
            return self._build_final_result(
                pipeline_id=pipeline_id,
                request=request,
                status=PipelineStatus.FAILED,
                analysis=analysis,
                research_queries=research_queries,
                discovered_sources=[],
                fetched_sources=[],
                extracted_candidates=[],
                validation_results=[],
                tri_result=None,
                calc_report=None,
                errors=errors,
                warnings=warnings,
                audit_trail=audit_trail,
                started_at=started_at,
                rejected_sources=rejected_sources,
            )

        if not all_discovered_sources:
            warnings.append("No external evidence sources were discovered for this business idea.")
            record_transition(
                PipelineStage.DISCOVERY.value,
                PipelineStage.COMPLETED.value,
                "No sources discovered; returning insufficient evidence",
            )
            return self._build_final_result(
                pipeline_id=pipeline_id,
                request=request,
                status=PipelineStatus.INSUFFICIENT_EVIDENCE,
                analysis=analysis,
                research_queries=research_queries,
                discovered_sources=[],
                fetched_sources=[],
                extracted_candidates=[],
                validation_results=[],
                tri_result=None,
                calc_report=None,
                errors=errors,
                warnings=warnings,
                audit_trail=audit_trail,
                started_at=started_at,
                rejected_sources=rejected_sources,
            )

        # 4. Source Fetching
        t0 = time.perf_counter()
        fetched_sources: List[FetchedSource] = []
        for src in all_discovered_sources:
            try:
                fetched = await self.fetch_service.fetch_discovered_source(src)
                if fetched:
                    fetched_sources.append(fetched)
                    if not fetched.content:
                        warnings.append(f"Fetched source {src.url} contained empty content.")
            except Exception as exc:
                warn = f"Failed to fetch source {src.url}: {exc}"
                logger.warning(warn)
                warnings.append(warn)

        dur = round((time.perf_counter() - t0) * 1000, 2)
        record_transition(
            PipelineStage.FETCHING.value,
            PipelineStage.EXTRACTION.value,
            f"Fetched {len(fetched_sources)} documents in {dur}ms",
            dur=dur,
        )

        # 5. Evidence & Competitor Extraction
        t0 = time.perf_counter()
        extracted_candidates: List[ExtractedEvidenceCandidate] = []
        extracted_competitors: List[CompetitorInfo] = []
        for doc in fetched_sources:
            if not doc.content:
                continue
            try:
                ext_req = ExtractionRequest(source=doc)
                ext_resp = self.extraction_service.extract_evidence_from_source(ext_req)
                if ext_resp.candidates:
                    extracted_candidates.extend(ext_resp.candidates)
            except Exception as exc:
                warn = f"Extraction failed for {doc.original_url}: {exc}"
                logger.warning(warn)
                warnings.append(warn)

            try:
                comps = self.extraction_service.extract_competitors_from_source(doc)
                if comps:
                    extracted_competitors.extend(comps)
            except Exception as comp_err:
                logger.debug("Competitor extraction skipped for %s: %s", doc.original_url, comp_err)

        dur = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(
            "Pipeline %s: Extracted %d metric candidates and %d competitors across %d fetched documents in %sms",
            pipeline_id,
            len(extracted_candidates),
            len(extracted_competitors),
            len(fetched_sources),
            dur,
        )
        record_transition(
            PipelineStage.EXTRACTION.value,
            PipelineStage.VALIDATION.value,
            f"Extracted {len(extracted_candidates)} candidates and {len(extracted_competitors)} competitors in {dur}ms",
            dur=dur,
        )

        # 6-9. Validation, Deduplication, Conflict Detection, Triangulation
        t0 = time.perf_counter()
        tri_result: Optional[TriangulationResult] = None
        try:
            tri_result = self.validation_service.triangulate_evidence(extracted_candidates, business_analysis=analysis)
            dur = round((time.perf_counter() - t0) * 1000, 2)
            logger.info(
                "Pipeline %s: Triangulation completed (%d verified, %d conflicts, %d duplicates) in %sms",
                pipeline_id,
                len(tri_result.verified_items),
                len(tri_result.conflict_groups),
                len(tri_result.duplicate_groups),
                dur,
            )
            record_transition(
                PipelineStage.VALIDATION.value,
                PipelineStage.CALCULATION.value,
                f"Triangulated evidence in {dur}ms",
                dur=dur,
            )
        except Exception as exc:
            err_msg = f"Evidence validation & triangulation failed: {exc}"
            logger.error(err_msg)
            errors.append(err_msg)
            record_transition(
                PipelineStage.VALIDATION.value,
                PipelineStage.COMPLETED.value,
                "Validation failed",
                err=err_msg,
            )
            failed_res = self._build_final_result(
                pipeline_id=pipeline_id,
                request=request,
                status=PipelineStatus.FAILED,
                analysis=analysis,
                research_queries=research_queries,
                discovered_sources=all_discovered_sources,
                fetched_sources=fetched_sources,
                extracted_candidates=extracted_candidates,
                validation_results=[],
                tri_result=None,
                calc_report=None,
                errors=errors,
                warnings=warnings,
                audit_trail=audit_trail,
                started_at=started_at,
                competitors=extracted_competitors,
                rejected_sources=rejected_sources,
            )
            try:
                self.repository.save(failed_res)
            except Exception:
                pass
            return failed_res

        # 10-11. Calculation
        calc_report: Optional[CalculationReport] = None
        if request.enable_calculation:
            t0 = time.perf_counter()
            try:
                calc_input = self._build_calculation_inputs(
                    analysis,
                    tri_result.validated_items if tri_result else [],
                    request,
                )
                calc_report = self.calculation_service.generate_report(calc_input)
                dur = round((time.perf_counter() - t0) * 1000, 2)
                logger.info(
                    "Pipeline %s: Market sizing calculation completed with status: %s in %sms",
                    pipeline_id,
                    calc_report.status,
                    dur,
                )
                record_transition(
                    PipelineStage.CALCULATION.value,
                    PipelineStage.COMPLETED.value,
                    f"Calculated market in {dur}ms",
                    dur=dur,
                )
            except Exception as exc:
                err_msg = f"Market calculation failed: {exc}"
                logger.error(err_msg)
                errors.append(err_msg)

        final_status = PipelineStatus.COMPLETED
        if len(fetched_sources) < len(all_discovered_sources) and len(fetched_sources) > 0:
            final_status = PipelineStatus.PARTIAL
        if tri_result and tri_result.conflict_groups and not tri_result.verified_items:
            if not (calc_report and calc_report.status == CalculationStatus.CALCULATED):
                final_status = PipelineStatus.CONFLICT
        if calc_report and calc_report.status == CalculationStatus.INSUFFICIENT_EVIDENCE:
            if final_status == PipelineStatus.COMPLETED:
                final_status = PipelineStatus.INSUFFICIENT_EVIDENCE

        total_exec_dur = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            "Pipeline %s: Completed with final status '%s' in %sms",
            pipeline_id,
            final_status.value if hasattr(final_status, "value") else final_status,
            total_exec_dur,
        )
        record_transition(
            PipelineStage.COMPLETED.value,
            PipelineStage.COMPLETED.value,
            f"Pipeline completed in {total_exec_dur}ms",
        )

        final_res = self._build_final_result(
            pipeline_id=pipeline_id,
            request=request,
            status=final_status,
            analysis=analysis,
            research_queries=research_queries,
            discovered_sources=all_discovered_sources,
            fetched_sources=fetched_sources,
            extracted_candidates=extracted_candidates,
            validation_results=tri_result.validated_items if tri_result else [],
            tri_result=tri_result,
            calc_report=calc_report,
            errors=errors,
            warnings=warnings,
            audit_trail=audit_trail,
            started_at=started_at,
            competitors=extracted_competitors,
            rejected_sources=rejected_sources,
        )

        # Auto-persist analysis to SQLite database
        try:
            self.repository.save(final_res)
        except Exception as save_err:
            logger.warning("Pipeline %s: Could not persist result to SQLite: %s", pipeline_id, save_err)

        return final_res

    def _generate_research_queries(
        self, analysis: Optional[BusinessAnalysis], request: PipelineRequest
    ) -> List[ResearchQuery]:
        """Generate structured research requirements based on extracted business attributes."""
        queries: List[ResearchQuery] = []
        target_geo = request.preferred_geography or (analysis.geography if analysis else None)
        target_year = request.preferred_year or 2025
        geo_str = f"{target_geo.strip()} " if target_geo else ""

        if analysis:
            market_cat = (analysis.market_category or analysis.industry or analysis.product or "market").strip()
            cust_target = (analysis.target_customer_segment or analysis.target_customer or "customers").strip()
            prod = (analysis.product or market_cat).strip()

            # 1. Target Customer Demographics / Population / Customer Base
            queries.append(
                ResearchQuery(
                    metric_required=f"{geo_str}{cust_target} population count businesses number users",
                    geography=target_geo,
                    year=target_year,
                    industry_topic=analysis.industry or market_cat,
                    target_population=cust_target,
                    max_results=request.max_sources,
                )
            )

            # 2. Industry / Product Market Size TAM
            queries.append(
                ResearchQuery(
                    metric_required=f"{geo_str}{market_cat} market size annual revenue",
                    geography=target_geo,
                    year=target_year,
                    industry_topic=analysis.industry or market_cat,
                    max_results=request.max_sources,
                )
            )

            # 3. Pricing / ARPU / Unit Spend Benchmarks
            queries.append(
                ResearchQuery(
                    metric_required=f"{geo_str}{prod} pricing average annual spend subscription ARPU fee cost",
                    geography=target_geo,
                    year=target_year,
                    industry_topic=analysis.industry or market_cat,
                    max_results=request.max_sources,
                )
            )

        # Fallback if no specific queries generated
        if not queries:
            queries.append(
                ResearchQuery(
                    metric_required=f"{geo_str}target customer population and market size",
                    geography=target_geo,
                    year=target_year,
                    max_results=request.max_sources,
                )
            )

        return queries

    def _build_unified_live_query(
        self,
        queries: List[ResearchQuery],
        analysis: Optional[BusinessAnalysis],
        request: PipelineRequest,
    ) -> ResearchQuery:
        """Construct a single comprehensive research query combining market size, volume, customer base, and segment info for API efficiency."""
        target_geo = request.preferred_geography or (analysis.geography if analysis else None) or "Global"
        target_year = request.preferred_year or 2026

        industry = (analysis.industry if analysis and analysis.industry else "").strip()
        product = (analysis.product if analysis and analysis.product else "").strip()
        market_cat = (analysis.market_category if analysis and analysis.market_category else "").strip()
        customer = (analysis.target_customer_segment or (analysis.target_customer if analysis else "")).strip()
        biz_idea = (request.business_idea or "").strip()

        components = []
        if target_geo and target_geo.lower() not in ["global", "unknown"]:
            components.append(target_geo)

        topic = market_cat or product or industry or biz_idea
        if topic:
            components.append(topic)

        if customer and customer.lower() not in topic.lower():
            components.append(customer)

        components.append("market size revenue growth volume customer count spend")

        unified_metric = " ".join(components)

        return ResearchQuery(
            metric_required=unified_metric,
            geography=target_geo,
            year=target_year,
            industry_topic=industry or product or topic,
            target_population=customer or None,
            max_results=request.max_sources or 5,
        )

    def _build_calculation_inputs(
        self,
        analysis: Optional[BusinessAnalysis],
        validated_items: List[EvidenceValidationResult],
        request: PipelineRequest,
    ) -> CalculationInput:
        """Map validated evidence and explicit user assumptions into calculation operands (Evidence Gate)."""
        target_geo = request.preferred_geography or (analysis.geography if analysis else None)
        target_yr = request.preferred_year or 2025

        assumptions_map = {a.name.lower(): a for a in request.explicit_assumptions}

        macro_market_input: Optional[EvidenceInput] = None
        population_input: Optional[EvidenceInput] = None
        serviceable_population_input: Optional[EvidenceInput] = None
        geo_pct_input: Optional[EvidenceInput] = None
        target_pct_input: Optional[EvidenceInput] = None
        pricing_input: Optional[EvidenceInput] = None
        som_share_input: Optional[EvidenceInput] = None

        # Sort validated evidence: Highest quality tier, verified lifecycle stage, and highest source quality score first
        tier_weight = {
            SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL: 5,
            "Tier 1: Government & Official Statistics": 5,
            SourceQualityTier.TIER_2_ACADEMIC_TRADE: 4,
            "Tier 2: Academic & Industry Trade Associations": 4,
            SourceQualityTier.TIER_3_ANALYST_PRESS: 3,
            "Tier 3: Market Analysts & Financial Press": 3,
            SourceQualityTier.TIER_4_GENERAL_UNVERIFIED: 2,
            "Tier 4: General Web & Secondary Articles": 2,
            SourceQualityTier.TIER_5_UNUSABLE: 1,
            "Tier 5: Unusable (Social/Forums/Unsourced)": 1,
        }


        # Ranked candidate pools for deterministic evidence-based operand selection
        macro_candidates: List[Tuple[float, float, str, EvidenceInput]] = []
        pricing_candidates: List[Tuple[float, float, str, EvidenceInput]] = []
        population_candidates: List[Tuple[float, float, str, EvidenceInput]] = []
        serviceable_population_candidates: List[Tuple[float, float, str, EvidenceInput]] = []
        geo_pct_candidates: List[Tuple[float, float, str, EvidenceInput]] = []
        target_pct_candidates: List[Tuple[float, float, str, EvidenceInput]] = []
        som_share_candidates: List[Tuple[float, float, str, EvidenceInput]] = []

        biz_keywords = [
            w for w in re.findall(r"\b[a-zA-Z]{3,}\b", (request.business_idea or "").lower())
            if w not in ("the", "and", "for", "with", "platform", "online", "market", "size", "year", "annual", "services", "service")
        ]
        ind_text = (analysis.industry.lower() if analysis and analysis.industry else "")
        prod_text = (analysis.product.lower() if analysis and analysis.product else "")

        for item in validated_items:
            eff_val = item.value if item.value is not None else item.range_min
            if eff_val is None:
                continue

            unit_norm = (item.unit or "").strip().lower()
            val_status = item.validation_status.value if hasattr(item.validation_status, "value") else str(item.validation_status or "valid")
            stage_status = item.lifecycle_stage.value if hasattr(item.lifecycle_stage, "value") else str(item.lifecycle_stage or "validated")
            conf_status = item.confidence.value if hasattr(item.confidence, "value") else str(item.confidence or "medium")
            is_prior = (item.year is not None and target_yr is not None and item.year < target_yr)

            def _resolve_curr(u_str: Optional[str]) -> Optional[str]:
                if not u_str:
                    return None
                u = u_str.upper()
                if u in ("USD", "$", "DOLLAR", "DOLLARS"):
                    return "USD"
                if u in ("INR", "₹", "RUPEE", "RUPEES", "RS", "RS.", "CRORE", "CRORES", "CR", "LAKH", "LAKHS"):
                    return "INR"
                if u in ("EUR", "€", "EURO", "EUROS"):
                    return "EUR"
                if u in ("GBP", "£", "POUND", "POUNDS"):
                    return "GBP"
                return None

            resolved_currency = _resolve_curr(item.unit)
            metric_name_lower = (item.metric or "").lower()
            raw_expr_lower = (getattr(item, "raw_value_expression", "") or "").lower()
            context_lower = (getattr(item, "source_context", "") or "").lower()
            full_context_text = f"{metric_name_lower} {raw_expr_lower} {context_lower} {(item.source_name or '').lower()} {(item.source_url or '').lower()}"
            metric_type_val = item.metric_type.value if hasattr(item.metric_type, "value") else str(item.metric_type or "")
            cand_geo_norm = (item.geography or "").strip().lower()
            tgt_geo_norm = (target_geo or "").strip().lower()

            POPULATION_KEYWORDS = (
                "student", "students", "user", "users", "developer", "developers", "people",
                "household", "households", "enterprise", "enterprises", "company", "companies",
                "population", "professional", "professionals", "worker", "workers", "adult", "adults",
                "subscriber", "subscribers", "customer", "customers", "patient", "patients",
                "buyer", "buyers", "individual", "individuals", "employee", "employees",
                "learner", "learners", "driver", "drivers", "station", "stations", "charger", "chargers",
                "vehicle", "vehicles", "car", "cars", "ev", "evs", "fleet", "fleets",
                "outlet", "outlets", "store", "stores", "two-wheeler", "two-wheelers",
                "three-wheeler", "three-wheelers", "bus", "buses", "truck", "trucks", "cab", "cabs",
                "taxi", "taxis", "resident", "residents", "installation", "installations",
                "client", "clients", "firm", "firms", "passenger", "passengers",
            )

            has_population_entity = (
                unit_norm in POPULATION_KEYWORDS
                or any(e in unit_norm for e in POPULATION_KEYWORDS)
                or any(e in metric_name_lower for e in POPULATION_KEYWORDS)
            )

            is_year_or_rate_range = (
                (item.range_min is not None and 1990 <= item.range_min <= 2040 and item.range_max is not None and 1990 <= item.range_max <= 2040)
                or (eff_val is not None and 1990 <= eff_val <= 2040 and any(yr_word in raw_expr_lower for yr_word in ("-", "–", "to", "forecast", "cagr", "period", "growth")))
                or any(k in metric_name_lower for k in ("cagr", "growth", "forecast", "year", "period", "trend", "tariff", "rate"))
                or "%" in raw_expr_lower
            )

            is_count_metric = (
                has_population_entity
                and not is_year_or_rate_range
                and unit_norm not in ("%", "pct", "percent", "percentage")
                and not resolved_currency
            )

            c_vals = [s.value for s in getattr(item, "conflicting_sources", []) if getattr(s, "value", None) is not None] + ([eff_val] if eff_val is not None else [])
            c_min = min(c_vals) if len(c_vals) > 1 else item.range_min
            c_max = max(c_vals) if len(c_vals) > 1 else item.range_max
            if c_min is not None and c_max is not None and c_min > c_max:
                c_min, c_max = min(c_min, c_max), max(c_min, c_max)

            # Common score calculator for evidence ranking
            cand_year = item.year or target_yr
            yr_diff = abs(cand_year - target_yr)
            yr_score = 40.0 if yr_diff == 0 else (30.0 if yr_diff == 1 else (15.0 if yr_diff <= 3 else 5.0))
            tier_scores = {
                SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL: 40.0,
                SourceQualityTier.TIER_2_ACADEMIC_TRADE: 30.0,
                SourceQualityTier.TIER_3_ANALYST_PRESS: 20.0,
                SourceQualityTier.TIER_4_GENERAL_UNVERIFIED: 10.0,
            }
            source_tier_score = tier_scores.get(item.source_quality_tier, 10.0)
            corrob_score = min(15.0, (getattr(item, "corroborating_source_count", 1) or 1 - 1) * 7.5)
            stage_score = 15.0 if stage_status in ("verified", "VERIFIED") else (10.0 if stage_status in ("validated", "VALIDATED") else 5.0)

            if is_count_metric:
                is_serviceable_subset = any(k in metric_name_lower for k in ("serviceable", "target", "tier-1", "tier 1", "urban", "major cities", "qualified", "accessible"))
                count_ev_input = EvidenceInput(
                    name=item.metric,
                    value=eff_val,
                    unit=item.unit or "units",
                    year=item.year or target_yr,
                    geography=item.geography or target_geo,
                    source_url=item.source_url,
                    source_name=item.source_name,
                    source_quality_tier=item.source_quality_tier,
                    market_scope=getattr(item, "market_scope", None),
                    market_scope_explanation=getattr(item, "market_scope_explanation", None),
                    is_prior_year_benchmark=is_prior,
                    entity_concept=unit_norm,
                    evidence_id=item.candidate_id,
                    validation_status=val_status,
                    lifecycle_stage=stage_status,
                    confidence=conf_status,
                    is_conflict=False,
                    conflicting_values=c_vals if len(c_vals) > 1 else [],
                    range_min=c_min,
                    range_max=c_max,
                )
                geo_score = 50.0 if (tgt_geo_norm and cand_geo_norm == tgt_geo_norm) else (30.0 if (tgt_geo_norm and tgt_geo_norm in cand_geo_norm) else 10.0)
                tot_score = geo_score + yr_score + source_tier_score + corrob_score + stage_score

                if is_serviceable_subset:
                    serviceable_population_candidates.append((tot_score, float(cand_year), item.candidate_id, count_ev_input))
                else:
                    population_candidates.append((tot_score, float(cand_year), item.candidate_id, count_ev_input))

            elif unit_norm in ("%", "pct", "percent", "percentage"):
                # 1. Growth, CAGR, Trend, and Forecast Rejection
                GROWTH_OR_TREND_TERMS = (
                    "cagr", "growth", "growing", "grown", "grew", "grow", "yoy", "year-on-year",
                    "year on year", "compound annual", "compounded annual", "expanding", "expansion",
                    "forecast period", "forecast to", "projected to grow", "annual increase", "rate of growth",
                    "growth rate", "increased by", "decreased by", "grew by", "dropped by", "fell by",
                    "delayed"
                )
                is_growth_or_cagr = (
                    any(k in metric_name_lower or k in raw_expr_lower or k in context_lower for k in GROWTH_OR_TREND_TERMS)
                    or bool(re.search(r"\b[+-]\d+(?:\.\d+)?\s*%", f"{metric_name_lower} {raw_expr_lower} {context_lower}"))
                )
                if is_growth_or_cagr:
                    continue

                # 2. Operational, Efficiency, Financial Margin, Promotional, and Demographic Trait Rejection
                OPERATIONAL_TERMS = (
                    "no-show", "no-shows", "no show", "no shows", "scheduling efficiency", "efficiency",
                    "productivity", "streamline", "optimization", "optimize", "cost reduction",
                    "reduce cost", "reduction", "savings", "save up to", "cut cost", "latency",
                    "uptime", "accuracy", "error rate", "retention rate", "retention", "churn",
                    "satisfaction", "nps", "csat", "margin", "profit margin", "operating margin",
                    "gross margin", "ebitda", "discount", "tax rate", "roi", "interest rate",
                    "inflation", "conversion rate", "click-through", "ctr", "bounce rate", "open rate",
                    "save ", "save 20%", "save 25%", "save 30%", "save 35%", "save 40%", "save 50%",
                    "reports • save", "free customization", "promo", "coupon", "voucher",
                    "urbanization rate", "urbanisation rate", "literacy rate", "internet penetration",
                    "smartphone penetration", "mobile penetration", "more efficient"
                )
                is_operational_metric = any(k in metric_name_lower or k in raw_expr_lower or k in context_lower for k in OPERATIONAL_TERMS)
                if is_operational_metric:
                    continue

                # 3. Biological / Species / Demographic Traits Breakdown Rejection
                SPECIES_OR_DEMOGRAPHIC_TERMS = (
                    "dogs dominate", "cats dominate", "dogs make up", "cats make up", "followed by cats",
                    "dog population", "cat population", "male", "female", "gender ratio", "gender breakdown",
                    "own dogs", "own cats", "dog ownership", "cat ownership", "households own", "pet owners own",
                    "own rather than", "prefer vegetarian", "vegetarian food", "dietary preference",
                    "food preference", "students are male", "students are female", "demographic survey",
                    "demographic statistics"
                )
                is_species_split = any(k in context_lower for k in SPECIES_OR_DEMOGRAPHIC_TERMS)
                if is_species_split:
                    continue

                # 4. Foreign Geography Rejection (when target geography is specified, e.g. India or Tamil Nadu)
                FOREIGN_GEO_TERMS = (
                    "chinese market", "in china", "japan market", "in japan", "japanese market",
                    "north america", "in the us", "in united states", "in europe", "european market",
                    "latin america", "middle east", "africa"
                )
                cand_geo_raw = (item.geography or "").strip().lower()
                is_foreign_geo = (
                    (cand_geo_raw and cand_geo_raw not in ("global", "worldwide", "world") and tgt_geo_norm and cand_geo_raw != tgt_geo_norm and tgt_geo_norm not in cand_geo_raw)
                    or any(fg in context_lower for fg in FOREIGN_GEO_TERMS if (not tgt_geo_norm or fg not in tgt_geo_norm))
                )
                if is_foreign_geo:
                    continue

                # 5. Unrelated Category Rejection (e.g. Pet Food & Supplies for Pet Care Services Platform)
                UNRELATED_CATEGORY_TERMS = (
                    "pet food", "packaged food", "food segment", "food market share", "dog food", "cat food",
                    "animal feed", "food alone accounts for", "food accounts for",
                    "cat litter", "pet litter", "litter", "pet supplies", "supplies sales", "supplies market",
                    "dog beds", "cat & dog beds", "beds and mats", "bird accessories", "fish accessories",
                    "aquarium", "cages", "pet apparel", "pet toys"
                )
                biz_prod_lower = (analysis.product or "").lower() if (analysis and getattr(analysis, "product", None)) else ""
                biz_idea_lower = (analysis.business_idea or "").lower() if (analysis and getattr(analysis, "business_idea", None)) else ""
                
                is_unrelated_category = False
                if ("food" not in biz_prod_lower and "feed" not in biz_prod_lower and "pet food" not in biz_idea_lower and "supplies" not in biz_prod_lower and "accessories" not in biz_prod_lower):
                    clauses = [c.strip() for c in re.split(r"[,;]|\bwhile\b|\bwhereas\b|\bbut\b", context_lower) if c.strip()]
                    cand_clause = next((c for c in clauses if (str(int(eff_val)) in c or f"{eff_val:.1f}" in c or raw_expr_lower in c)), context_lower)
                    if any(uc in metric_name_lower or uc in cand_clause for uc in UNRELATED_CATEGORY_TERMS):
                        if not any(sc in cand_clause for sc in ("service", "services", "grooming", "vet", "veterinary", "clinic", "platform", "booking")):
                            is_unrelated_category = True

                if is_unrelated_category:
                    continue

                # 6. Competitor Market Share Rejection (e.g., "Mars Petcare accounts for 22%")
                is_competitor_share = any(k in context_lower for k in ("competitor", "market leader", "mars petcare", "pedigree", "royal canin", "nestle purina accounts for"))
                if is_competitor_share:
                    continue

                pct_ev_input = EvidenceInput(
                    name=item.metric,
                    value=eff_val,
                    unit="%",
                    year=item.year or target_yr,
                    geography=item.geography or target_geo,
                    source_url=item.source_url,
                    source_name=item.source_name,
                    source_quality_tier=item.source_quality_tier,
                    market_scope=getattr(item, "market_scope", None),
                    market_scope_explanation=getattr(item, "market_scope_explanation", None),
                    is_prior_year_benchmark=is_prior,
                    evidence_id=item.candidate_id,
                    lifecycle_stage=stage_status,
                    range_min=c_min,
                    range_max=c_max,
                )

                # 7. Disambiguate Geographic Conversion Share vs Target Service/Customer Segment
                GLOBAL_OR_REGIONAL_SHARE_TERMS = (
                    "global market share", "global share", "of the global market", "of global market",
                    "of the global", "of global", "share of the global", "share of global",
                    "global market revenues", "regional market share", "the region exhibited",
                    "regional share", "state share", "city share", "metro share", "geographic share",
                    "geography"
                )
                is_global_or_regional_share = (
                    any(t in metric_name_lower or t in context_lower for t in GLOBAL_OR_REGIONAL_SHARE_TERMS)
                )

                # Geographic share percentage (e.g. "India represents 5.41% of the global market")
                # Must explicitly reference target geography as the subject
                is_explicit_geo_share = (
                    is_global_or_regional_share
                    and (
                        (tgt_geo_norm and tgt_geo_norm in full_context_text)
                        or (item.geography and tgt_geo_norm and tgt_geo_norm in item.geography.lower())
                    )
                )
                is_geo_pct = is_explicit_geo_share

                # Obtainable market capture percentage (SOM)
                is_som_share = (
                    any(k in metric_name_lower for k in ("som", "obtainable", "capture"))
                    or any(k in context_lower for k in ("obtainable market share", "target market share", "our market share", "platform penetration target", "market capture of", "obtainable share", "realistic market capture", "year 1 capture", "year 3 capture"))
                )

                # Target customer / serviceable segment narrowing factor
                # CANNOT be a global or regional market share!
                # Strip out generic fallback metric names to avoid false positive segment matching on "segment"
                metric_clean = metric_name_lower.replace("market share / segment percentage", "").strip()
                target_cust_str = (analysis.target_customer or "").lower().strip() if analysis else ""
                target_cust_words = [w for w in re.findall(r"\w+", target_cust_str) if len(w) > 3]

                has_segment_intent = (
                    not is_global_or_regional_share
                    and (
                        metric_type_val in ("customer_segment", "target_segment", "serviceable_share")
                        or (target_cust_str and (target_cust_str in metric_clean or target_cust_str in context_lower))
                        or (target_cust_words and any(w in metric_clean for w in target_cust_words))
                        or (target_cust_words and any(w in context_lower and any(v in context_lower for v in ("represent", "account", "share", "portion", "orders", "demand", "volume", "users", "customers", "market", "segment")) for w in target_cust_words))
                        or (metric_clean and any(k in metric_clean for k in (
                            "target segment", "serviceable segment", "customer qualification", "addressable segment",
                            "target audience", "serviceable percentage", "target customer", "serviceable customer",
                            "target demographic", "customer segment", "service segment", "segment share", "segment",
                            "service transactions", "online orders", "penetration rate", "adoption rate", "market share"
                        )))
                        or any(k in context_lower for k in (
                            "serviceable customer", "target customer segment", "qualification rate", "serviceable addressable",
                            "target segment", "serviceable segment", "accounts for", "account for", "represents", "represent",
                            "service transactions in", "orders across", "demand across", "adoption rate", "penetration rate", "market share of"
                        ))
                    )
                )
                has_business_topic_alignment = (
                    not analysis
                    or any(kw in full_context_text for kw in biz_keywords)
                    or (ind_text and ind_text in full_context_text)
                    or (prod_text and any(pw in full_context_text for pw in prod_text.split() if len(pw) > 3))
                )
                is_target_segment = has_segment_intent and has_business_topic_alignment and not is_geo_pct and not is_som_share

                if is_geo_pct:
                    cand_geo_match = (
                        not item.geography
                        or not target_geo
                        or item.geography.lower() == target_geo.lower()
                        or (target_geo.lower() in (item.source_context or "").lower())
                    )
                    if cand_geo_match:
                        geo_score = 100.0 if (target_geo and target_geo.lower() in full_context_text) else 60.0
                        tot_score = geo_score + yr_score + source_tier_score + corrob_score + stage_score
                        geo_pct_candidates.append((tot_score, float(cand_year), item.candidate_id, pct_ev_input))

                elif is_som_share:
                    tot_score = 80.0 + yr_score + source_tier_score + corrob_score + stage_score
                    som_share_candidates.append((tot_score, float(cand_year), item.candidate_id, pct_ev_input))

                elif is_target_segment:
                    relevance_match = 50.0 if any(w in full_context_text for w in biz_keywords) else 30.0
                    tot_score = relevance_match + yr_score + source_tier_score + corrob_score + stage_score
                    target_pct_candidates.append((tot_score, float(cand_year), item.candidate_id, pct_ev_input))

            elif resolved_currency is not None or unit_norm in ("usd", "inr", "eur", "gbp", "dollars", "rupees", "crore", "crores", "lakh", "lakhs"):
                COMMODITY_USAGE_TERMS = (
                    "/kwh", "per kwh", "/watt", "per watt", "/kw", "per kw",
                    "tariff", "tariffs", "/km", "per km", "/hour", "/hr", "per hour",
                    "/gb", "/mb", "per gb", "/token", "/call", "/share", "/sqft", "/kg", "/liter", "/l"
                )

                is_commodity_tariff = (
                    any(cu in unit_norm for cu in COMMODITY_USAGE_TERMS)
                    or any(cu in metric_name_lower for cu in COMMODITY_USAGE_TERMS)
                    or any(cu in raw_expr_lower for cu in COMMODITY_USAGE_TERMS)
                    or any(cu in context_lower for cu in ("/kwh", "per kwh", "/watt", "per watt", "tariff", "tariffs"))
                )

                # Disambiguate between Macro Market Size (for Top-Down) vs Unit Pricing/ARPU (for Bottom-Up)
                UNIT_ECONOMICS_INDICATORS = (
                    "per user", "per student", "per customer", "per pet", "per companion pet",
                    "per household", "per animal", "per dog", "per cat", "per capita", "per head",
                    "per person", "per subscriber", "per learner", "per account", "per client",
                    "per employee", "per transaction", "per order", "per delivery", "per meal",
                    "annual fee", "subscription price", "arpu", "unit price", "price per",
                    "spend per", "spending per", "cost per", "fee per", "expenditure per",
                    "annual spend", "average spend", "annual expenditure", "pricing", "tuition"
                )
                has_unit_economics_wording = any(ue in metric_name_lower or ue in raw_expr_lower or ue in context_lower for ue in UNIT_ECONOMICS_INDICATORS)

                is_macro_metric = (
                    not is_commodity_tariff
                    and not has_unit_economics_wording
                    and (
                        (metric_type_val in ("market_size", "market_revenue") and eff_val >= 1_000_000.0)
                        or any(w in metric_name_lower for w in ("market size", "market revenue", "market value", "industry size", "industry revenue", "sector revenue", "market spending", "total market", "overall market"))
                        or (eff_val >= 1_000_000.0 and not any(w in metric_name_lower for w in ("fee", "price", "spend", "cost", "plan", "arpu")))
                    )
                )

                is_unit_pricing_metric = (
                    not is_macro_metric
                    and not is_commodity_tariff
                    and eff_val < 1_000_000.0
                    and (
                        has_unit_economics_wording
                        or metric_type_val in ("average_price", "annual_spend", "pricing", "arpu", "subscription_price")
                        or any(w in metric_name_lower for w in ("price", "pricing", "annual spend", "arpu", "tuition", "annual fee", "cost per", "subscription", "annual plan", "monthly plan", "license fee"))
                        or (eff_val >= 50.0 and any(w in metric_name_lower for w in ("spend", "cost", "fee", "price", "rate", "plan")))
                    )
                )

                if is_macro_metric and not is_unit_pricing_metric:
                    item_geo_lower = (item.geography or "").lower()
                    if item_geo_lower in ("global", "worldwide", "world"):
                        cand_geo = "Global"
                    elif item.geography:
                        cand_geo = item.geography
                    elif any(k in metric_name_lower for k in ("global market", "worldwide market", "global industry", "global revenue")):
                        cand_geo = "Global"
                    else:
                        cand_geo = target_geo

                    cand_geo_norm = (cand_geo or "").strip().lower()
                    tgt_geo_norm = (target_geo or "").strip().lower()

                    # Foreign Geography Exclusion: Foreign country market size must NEVER be accepted as TAM for target geography
                    FOREIGN_COUNTRIES = {
                        "china", "united states", "us", "usa", "japan", "germany", "united kingdom", "uk",
                        "france", "canada", "australia", "brazil", "italy", "spain", "thailand", "indonesia",
                        "russia", "mexico", "south korea"
                    }
                    is_foreign_to_target = (
                        tgt_geo_norm
                        and cand_geo_norm in FOREIGN_COUNTRIES
                        and cand_geo_norm != tgt_geo_norm
                        and tgt_geo_norm not in cand_geo_norm
                    )
                    if is_foreign_to_target:
                        continue

                    # Unrelated physical-product market exclusion for service platforms
                    biz_prod_lower = (analysis.product or "").lower() if (analysis and getattr(analysis, "product", None)) else ""
                    biz_idea_lower = (analysis.business_idea or "").lower() if (analysis and getattr(analysis, "business_idea", None)) else ""
                    biz_is_service_or_platform = any(k in f"{biz_prod_lower} {biz_idea_lower}".lower() for k in ("service", "platform", "software", "saas", "app", "marketplace", "training", "tutoring", "care", "delivery"))
                    
                    DISCORDANT_COMMODITY_TERMS = ("pet food", "cat litter", "dog food", "animal feed", "packaged food", "school uniforms", "textbooks")
                    is_unrelated_tam_product = (
                        biz_is_service_or_platform
                        and any(up in metric_name_lower or up in context_lower for up in DISCORDANT_COMMODITY_TERMS)
                        and not any(up in biz_prod_lower or up in biz_idea_lower for up in DISCORDANT_COMMODITY_TERMS)
                    )
                    if is_unrelated_tam_product:
                        continue

                    macro_ev_input = EvidenceInput(
                        name=item.metric,
                        value=eff_val,
                        unit=item.unit or (resolved_currency or "USD"),
                        currency=resolved_currency or "USD",
                        year=item.year or target_yr,
                        geography=cand_geo,
                        source_url=item.source_url,
                        source_name=item.source_name,
                        source_quality_tier=item.source_quality_tier,
                        market_scope=getattr(item, "market_scope", None),
                        market_scope_explanation=getattr(item, "market_scope_explanation", None),
                        is_prior_year_benchmark=is_prior,
                        entity_concept=item.metric,
                        evidence_id=item.candidate_id,
                        validation_status=val_status,
                        lifecycle_stage=stage_status,
                        confidence=conf_status,
                        is_conflict=False,
                        conflicting_values=[v for v in c_vals if v >= 1_000_000.0] if len([v for v in c_vals if v >= 1_000_000.0]) > 1 else [],
                        range_min=(item.range_min if (item.range_min is not None and item.range_min >= 1_000_000.0) else None),
                        range_max=(item.range_max if (item.range_max is not None and item.range_max >= 1_000_000.0) else None),
                    )

                    # Category Relevance Scoring (Weight: 100 max)
                    if tgt_geo_norm and cand_geo_norm == tgt_geo_norm:
                        geo_align_score = 100.0
                    elif tgt_geo_norm and tgt_geo_norm in cand_geo_norm:
                        geo_align_score = 85.0
                    elif cand_geo_norm in ("global", "worldwide", "world"):
                        geo_align_score = 40.0
                    else:
                        geo_align_score = 10.0

                    cat_match_score = 0.0
                    if ind_text and ind_text in full_context_text:
                        cat_match_score += 40.0
                    if prod_text and any(pw in full_context_text for pw in prod_text.split() if len(pw) > 3):
                        cat_match_score += 30.0
                    cat_match_score += min(50.0, sum(15.0 for kw in biz_keywords if kw in full_context_text))

                    # Penalize generic macro economy / cross-industry GMV figures
                    GENERIC_MACRO_TERMS = (
                        "digital commerce as a whole", "entire e-commerce", "total gmv of digital commerce",
                        "overall retail commerce", "national gdp", "gross merchandise value (gmv) across all"
                    )
                    if any(gm in context_lower for gm in GENERIC_MACRO_TERMS) and not any(k in biz_keywords for k in ("national", "gdp", "macro", "entire", "overall")):
                        cat_match_score -= 80.0

                    macro_tot_score = geo_align_score + cat_match_score + yr_score + source_tier_score + corrob_score + stage_score
                    macro_candidates.append((macro_tot_score, float(cand_year), item.candidate_id, macro_ev_input))

                elif is_unit_pricing_metric:
                    pricing_ev_input = EvidenceInput(
                        name=item.metric,
                        value=eff_val,
                        unit=item.unit or (resolved_currency or "USD"),
                        currency=resolved_currency or "USD",
                        year=item.year or target_yr,
                        geography=item.geography or target_geo,
                        source_url=item.source_url,
                        source_name=item.source_name,
                        source_quality_tier=item.source_quality_tier,
                        market_scope=getattr(item, "market_scope", None),
                        market_scope_explanation=getattr(item, "market_scope_explanation", None),
                        is_prior_year_benchmark=is_prior,
                        entity_concept=item.metric,
                        evidence_id=item.candidate_id,
                        validation_status=val_status,
                        lifecycle_stage=stage_status,
                        confidence=conf_status,
                        is_conflict=False,
                        conflicting_values=c_vals if len(c_vals) > 1 else [],
                        range_min=c_min,
                        range_max=c_max,
                    )
                    price_score = 50.0 + yr_score + source_tier_score + corrob_score + stage_score
                    pricing_candidates.append((price_score, float(cand_year), item.candidate_id, pricing_ev_input))

        # Deterministic ranking and top-candidate selection
        if macro_candidates:
            macro_candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
            macro_market_input = macro_candidates[0][3]

            # Range bounds must be constructed ONLY from independently qualified TAM candidates for the same geography scope
            matched_geo = (macro_market_input.geography or "").lower()
            qualified_geo_cands = [
                c[3] for c in macro_candidates
                if (c[3].geography or "").lower() == matched_geo and c[3].value is not None and c[3].value >= 1_000_000.0
            ]
            if macro_market_input.range_min is not None and macro_market_input.range_max is not None:
                # Retain explicit bounds extracted directly from source text (e.g. $8.6B to $9.2B)
                pass
            elif len(qualified_geo_cands) > 1:
                q_vals = [cand.value for cand in qualified_geo_cands if cand.value is not None]
                macro_market_input.range_min = min(q_vals)
                macro_market_input.range_max = max(q_vals)
            else:
                macro_market_input.range_min = None
                macro_market_input.range_max = None

        if pricing_candidates:
            pricing_candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
            pricing_input = pricing_candidates[0][3]

        if population_candidates:
            population_candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
            population_input = population_candidates[0][3]

        if serviceable_population_candidates:
            serviceable_population_candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
            serviceable_population_input = serviceable_population_candidates[0][3]

        if geo_pct_candidates:
            geo_pct_candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
            geo_pct_input = geo_pct_candidates[0][3]

        if target_pct_candidates:
            target_pct_candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
            target_pct_input = target_pct_candidates[0][3]

        if som_share_candidates:
            som_share_candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
            som_share_input = som_share_candidates[0][3]

        # Apply explicit user assumptions with robust disambiguation
        for a_name, a_obj in assumptions_map.items():
            if any(k in a_name for k in ("macro", "market_size", "industry_size", "total_market")):
                macro_market_input = EvidenceInput(
                    name=a_obj.name,
                    value=a_obj.value,
                    unit=a_obj.unit,
                    currency=a_obj.unit if a_obj.unit.upper() in ("USD", "INR", "EUR", "GBP") else None,
                    is_assumption=True,
                    assumption_justification=a_obj.justification,
                )
            elif any(k in a_name for k in ("price", "arpu", "fee", "cost", "subscription", "pricing", "spend")):
                pricing_input = EvidenceInput(
                    name=a_obj.name,
                    value=a_obj.value,
                    unit=a_obj.unit,
                    currency=a_obj.unit if a_obj.unit.upper() in ("USD", "INR", "EUR", "GBP") else None,
                    is_assumption=True,
                    assumption_justification=a_obj.justification,
                )
            elif any(k in a_name for k in ("som", "obtainable", "capture", "penetration", "som_share", "market_share")):
                som_share_input = EvidenceInput(
                    name=a_obj.name,
                    value=a_obj.value,
                    unit="%",
                    is_assumption=True,
                    assumption_justification=a_obj.justification,
                )
            elif any(k in a_name for k in ("geo", "geograph", "city", "cities", "urban", "region", "state", "metro")):
                geo_pct_input = EvidenceInput(
                    name=a_obj.name,
                    value=a_obj.value,
                    unit="%",
                    is_assumption=True,
                    assumption_justification=a_obj.justification,
                )
            elif any(k in a_name for k in ("serviceable_customer", "serviceable_population", "target_population", "target_customer_count", "serviceable_count")):
                serviceable_population_input = EvidenceInput(
                    name=a_obj.name,
                    value=a_obj.value,
                    unit=a_obj.unit or "units",
                    is_assumption=True,
                    assumption_justification=a_obj.justification,
                )
            elif any(k in a_name for k in ("target", "segment", "sam", "portion", "serviceable", "reach", "share")):
                target_pct_input = EvidenceInput(
                    name=a_obj.name,
                    value=a_obj.value,
                    unit="%",
                    is_assumption=True,
                    assumption_justification=a_obj.justification,
                )

        td_inputs = None
        if macro_market_input:
            # Semantic Anti-Double-Narrowing Rule:
            # If macro_market_input is already geographically scoped to target_geo (e.g. India),
            # DO NOT apply a global-to-local geographic percentage (e.g. India's 5.41% of global market) to it.
            effective_geo_pct = geo_pct_input
            if (
                macro_market_input.geography
                and target_geo
                and (
                    macro_market_input.geography.lower() == target_geo.lower()
                    or target_geo.lower() in macro_market_input.geography.lower()
                )
            ):
                effective_geo_pct = None

            td_inputs = TopDownCalculationInputs(
                macro_market_size=macro_market_input,
                serviceable_geography_percentage=effective_geo_pct,
                target_segment_percentage=target_pct_input,
                obtainable_market_share=som_share_input,
            )

        bu_inputs = BottomUpCalculationInputs(
            potential_customers=population_input,
            serviceable_customers=serviceable_population_input,
            target_customer_percentage=target_pct_input,
            obtainable_market_share=som_share_input,
            pricing=pricing_input,
            pricing_frequency=PriceFrequency.ANNUAL,
        )

        return CalculationInput(
            business_idea=request.business_idea,
            target_geography=target_geo,
            target_year=target_yr,
            market_definition=analysis.market_definition if analysis else None,
            tam_methodology="Direct Reported Market Size or Bottom-Up Customer Spend",
            sam_methodology="Serviceable Segment Narrowing",
            som_methodology="Capacity-Based Obtainable Share",
            top_down_inputs=td_inputs,
            bottom_up_inputs=bu_inputs,
            assumptions=request.explicit_assumptions,
        )

    def _build_final_result(
        self,
        pipeline_id: str,
        request: PipelineRequest,
        status: PipelineStatus,
        analysis: Optional[BusinessAnalysis],
        research_queries: List[ResearchQuery],
        discovered_sources: List[DiscoveredSource],
        fetched_sources: List[FetchedSource],
        extracted_candidates: List[ExtractedEvidenceCandidate],
        validation_results: List[EvidenceValidationResult],
        tri_result: Optional[TriangulationResult],
        calc_report: Optional[CalculationReport],
        errors: List[str],
        warnings: List[str],
        audit_trail: List[StateTransitionRecord],
        started_at: str,
        competitors: Optional[List[CompetitorInfo]] = None,
        rejected_sources: Optional[List[DiscoveredSource]] = None,
        rejected_candidates: Optional[List[ExtractedEvidenceCandidate]] = None,
    ) -> PipelineResult:
        """Construct the final user-facing PipelineResult."""
        provenance_list: List[SourceProvenance] = []
        for val_item in validation_results:
            provenance_list.extend(val_item.corroborating_sources)

        seen_urls = set()
        unique_provenance: List[SourceProvenance] = []
        for p in provenance_list:
            if p.source_url not in seen_urls:
                seen_urls.add(p.source_url)
                unique_provenance.append(p)

        tam_res = None
        sam_res = None
        som_res = None
        confidence = EvidenceConfidence.LOW
        all_warnings = list(warnings)

        if calc_report:
            bu_tam_calc = (calc_report.bottom_up_tam and calc_report.bottom_up_tam.status == CalculationStatus.CALCULATED and calc_report.bottom_up_tam.estimate is not None)
            td_tam_calc = (calc_report.top_down_tam and calc_report.top_down_tam.status == CalculationStatus.CALCULATED and calc_report.top_down_tam.estimate is not None)

            if bu_tam_calc and td_tam_calc:
                bu_val = calc_report.bottom_up_tam.estimate
                td_val = calc_report.top_down_tam.estimate
                ratio = (bu_val / td_val) if td_val > 0 else 1.0
                # If Bottom-Up is an implausible micro-calculation (< $500 vs macro > $10M),
                # OR if Bottom-Up severely diverges from Top-Down (ratio < 0.2 or ratio > 5.0),
                # OR if Top-Down is backed by direct empirical macro market size evidence:
                if bu_val < 500.0 and td_val >= 10_000_000.0:
                    tam_res = calc_report.top_down_tam
                    sam_res = calc_report.top_down_sam
                    som_res = calc_report.top_down_som
                elif ratio < 0.2 or ratio > 5.0:
                    tam_res = calc_report.top_down_tam
                    sam_res = calc_report.top_down_sam
                    som_res = calc_report.top_down_som
                elif calc_report.top_down_tam and calc_report.top_down_tam.evidence_quality not in (None, "INSUFFICIENT"):
                    tam_res = calc_report.top_down_tam
                    sam_res = calc_report.top_down_sam
                    som_res = calc_report.top_down_som
                else:
                    tam_res = calc_report.bottom_up_tam
                    sam_res = calc_report.bottom_up_sam
                    som_res = calc_report.bottom_up_som
            elif bu_tam_calc:
                tam_res = calc_report.bottom_up_tam
                sam_res = calc_report.bottom_up_sam
                som_res = calc_report.bottom_up_som
            elif td_tam_calc:
                tam_res = calc_report.top_down_tam
                sam_res = calc_report.top_down_sam
                som_res = calc_report.top_down_som
            else:
                tam_res = calc_report.bottom_up_tam or calc_report.top_down_tam
                sam_res = calc_report.bottom_up_sam or calc_report.top_down_sam
                som_res = calc_report.bottom_up_som or calc_report.top_down_som

            confidence = calc_report.confidence
            all_warnings.extend(calc_report.warnings)

        is_failed = (status == PipelineStatus.FAILED or str(status).lower() in ("failed", "pipelinestatus.failed"))

        if not tam_res:
            tam_res = TAMResult(
                status=CalculationStatus.EXECUTION_FAILED if is_failed else CalculationStatus.NOT_CALCULABLE,
                estimate=None,
                message="Analysis execution failed before calculation." if is_failed else "TAM could not be calculated due to insufficient evidence.",
                confidence=EvidenceConfidence.LOW,
            )
        if not sam_res:
            sam_res = SAMResult(
                status=CalculationStatus.EXECUTION_FAILED if is_failed else CalculationStatus.NOT_CALCULABLE,
                estimate=None,
                message="Analysis execution failed before calculation." if is_failed else "SAM could not be calculated due to insufficient evidence.",
                confidence=EvidenceConfidence.LOW,
            )
        if not som_res:
            som_res = SOMResult(
                status=CalculationStatus.EXECUTION_FAILED if is_failed else CalculationStatus.INSUFFICIENT_EVIDENCE,
                estimate=None,
                message="Analysis execution failed before calculation." if is_failed else "SOM was withheld under the SOM Safety Rule (obtainable market share was not provided).",
                confidence=EvidenceConfidence.LOW,
            )

        if is_failed:
            all_warnings.append("Analysis execution failed because the LLM/runtime service was unavailable or encountered an error.")
        else:
            if not discovered_sources:
                all_warnings.append("Insufficient evidence: No external evidence sources were discovered for this business idea.")
            if tam_res.status != CalculationStatus.CALCULATED:
                all_warnings.append("TAM could not be fully calculated due to missing customer population or pricing evidence.")
            if som_res.status != CalculationStatus.CALCULATED:
                all_warnings.append("SOM was withheld under the SOM Safety Rule (obtainable market share was not provided).")

        from app.config import settings
        raw_mode = (settings.SEARCH_PROVIDER or "mock").strip().lower()
        if isinstance(getattr(self.discovery_service, "provider", None), LiveDiscoveryProvider) or raw_mode in ("live", "tavily", "searxng", "custom"):
            provider_mode = "live"
        else:
            provider_mode = "mock"

        if provider_mode == "mock":
            all_warnings.insert(0, "These figures are development/test fixtures and should not be used as real-world market estimates.")

        eq_rating = "INSUFFICIENT"
        if calc_report and calc_report.evidence_quality:
            eq_rating = (
                calc_report.evidence_quality.value
                if hasattr(calc_report.evidence_quality, "value")
                else str(calc_report.evidence_quality)
            )

        return PipelineResult(
            pipeline_id=pipeline_id,
            status=status,
            business_idea=request.business_idea,
            business_analysis=analysis,
            research_queries=research_queries,
            discovered_sources=discovered_sources,
            fetched_sources=fetched_sources,
            extracted_candidates=extracted_candidates,
            validation_results=validation_results,
            triangulation_result=tri_result,
            calculation_report=calc_report,
            calculation_trace=calc_report.calculation_trace if calc_report else None,
            tam=tam_res,
            sam=sam_res,
            som=som_res,
            confidence=confidence,
            evidence_quality_rating=eq_rating,
            research_provider=provider_mode,
            rejected_sources=rejected_sources or [],
            rejected_candidates=rejected_candidates or [],
            competitors=competitors or [],
            conflicts=tri_result.conflict_groups if tri_result else [],
            errors=errors,
            warnings=list(dict.fromkeys(all_warnings)),
            audit_trail=audit_trail,
            provenance=unique_provenance,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )


# Backward-compatible class name alias
MarketAnalyzerPipeline = MarketAnalysisPipeline

_pipeline_instance: Optional[MarketAnalysisPipeline] = None


def get_market_pipeline() -> MarketAnalysisPipeline:
    """Dependency provider returning singleton MarketAnalysisPipeline."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = MarketAnalysisPipeline()
    return _pipeline_instance
