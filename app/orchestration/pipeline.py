from datetime import datetime, timezone
import logging
import time
from typing import AsyncGenerator, List, Optional
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
            err_msg = f"Business analysis failed: {exc}"
            logger.error(err_msg)
            errors.append(err_msg)
            record_transition(
                PipelineStage.BUSINESS_ANALYSIS.value,
                PipelineStage.COMPLETED.value,
                "Business analysis step failed",
                err=err_msg,
            )
            yield create_progress_event(
                pipeline_id,
                PipelineStage.BUSINESS_ANALYSIS,
                PipelineStatus.FAILED,
                err_msg,
                progress_percent=100,
            )
            return

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
                discovered_sources=discovered_sources,
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
            # 1. Target Customer Demographics / Population
            if analysis.target_customer:
                cust = analysis.target_customer.strip()
                queries.append(
                    ResearchQuery(
                        metric_required=f"{geo_str}{cust} population enrollment count",
                        geography=target_geo,
                        year=target_year,
                        industry_topic=analysis.industry,
                        target_population=cust,
                        max_results=request.max_sources,
                    )
                )
            elif analysis.industry:
                queries.append(
                    ResearchQuery(
                        metric_required=f"{geo_str}target customer population in {analysis.industry.strip()}",
                        geography=target_geo,
                        year=target_year,
                        industry_topic=analysis.industry.strip(),
                        max_results=request.max_sources,
                    )
                )

            # 2. Industry / Product Market Size TAM
            if analysis.industry:
                queries.append(
                    ResearchQuery(
                        metric_required=f"{geo_str}{analysis.industry.strip()} market size revenue",
                        geography=target_geo,
                        year=target_year,
                        industry_topic=analysis.industry.strip(),
                        max_results=request.max_sources,
                    )
                )
            elif analysis.product:
                queries.append(
                    ResearchQuery(
                        metric_required=f"{geo_str}{analysis.product.strip()} market size revenue",
                        geography=target_geo,
                        year=target_year,
                        industry_topic=analysis.product.strip(),
                        max_results=request.max_sources,
                    )
                )

            # 3. Pricing / ARPU Benchmarks
            if analysis.product:
                queries.append(
                    ResearchQuery(
                        metric_required=f"{geo_str}{analysis.product.strip()} course pricing subscription cost ARPU",
                        geography=target_geo,
                        year=target_year,
                        industry_topic=analysis.industry,
                        max_results=request.max_sources,
                    )
                )
            elif analysis.industry:
                queries.append(
                    ResearchQuery(
                        metric_required=f"{geo_str}{analysis.industry.strip()} pricing subscription cost ARPU",
                        geography=target_geo,
                        year=target_year,
                        industry_topic=analysis.industry.strip(),
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
        customer = (analysis.target_customer if analysis and analysis.target_customer else "").strip()
        biz_idea = (request.business_idea or "").strip()

        components = []
        if target_geo and target_geo.lower() not in ["global", "unknown"]:
            components.append(target_geo)

        topic = product or industry or biz_idea
        if topic:
            components.append(topic)

        if customer and customer.lower() not in topic.lower():
            components.append(customer)

        components.append("market size revenue growth volume customer count")

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
        sorted_items = sorted(
            validated_items,
            key=lambda x: (
                1 if x.lifecycle_stage in ("verified", DiscoveryLifecycleStage.VERIFIED) else 0,
                tier_weight.get(x.source_quality_tier, 2),
                x.source_quality_score or 0.0,
                x.relevance_score or 0.0,
            ),
            reverse=True,
        )

        # Filter: ONLY validated / verified items from credible tiers may pass the gate
        for item in sorted_items:
            if not item.is_valid:
                continue
            if item.source_quality_tier in (SourceQualityTier.TIER_5_UNUSABLE, "Tier 5: Unusable (Social/Forums/Unsourced)"):
                continue
            unit_norm = (item.unit or "").lower()
            val_status = item.validation_status.value if hasattr(item.validation_status, "value") else str(item.validation_status or "valid")
            stage_status = item.lifecycle_stage.value if hasattr(item.lifecycle_stage, "value") else str(item.lifecycle_stage or "validated")
            conf_status = item.confidence.value if hasattr(item.confidence, "value") else str(item.confidence or "medium")
            is_prior = bool(item.year is not None and target_yr is not None and item.year == target_yr - 1)

            eff_val = item.value if item.value is not None else ((item.range_min + item.range_max) / 2.0 if (item.range_min is not None and item.range_max is not None) else None)
            if eff_val is None:
                continue

            # Currency resolution helper
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
            is_count_metric = (
                unit_norm in (
                    "students", "student", "users", "user", "developers", "people",
                    "households", "enterprises", "companies", "population", "professionals",
                    "professional", "workers", "adults", "subscribers", "customers",
                    "patients", "buyers", "individuals", "employees", "learners", "drivers",
                    "stations", "station", "chargers", "charger", "ports", "port",
                    "vehicles", "vehicle", "cars", "car", "evs", "ev", "fleets", "fleet",
                    "units", "unit", "locations", "outlets", "stores", "store",
                    "two-wheelers", "two-wheeler", "three-wheelers", "three-wheeler",
                    "buses", "bus", "trucks", "truck", "cabs", "cab", "taxis", "taxi",
                )
                or any(c in unit_norm for c in (
                    "student", "user", "developer", "people", "professional", "worker",
                    "adult", "subscriber", "customer", "person", "population", "household",
                    "enterprise", "company", "employee", "buyer", "station", "charger",
                    "vehicle", "car", "port", "outlet", "device", "fleet", "unit",
                ))
            )

            if is_count_metric and not resolved_currency:
                metric_lower = (item.metric or "").lower()
                is_serviceable_subset = any(k in metric_lower for k in ("serviceable", "target", "tier-1", "tier 1", "urban", "major cities", "qualified", "accessible"))
                c_vals = [s.value for s in getattr(item, "conflicting_sources", []) if getattr(s, "value", None) is not None] + ([eff_val] if eff_val is not None else [])
                c_min = min(c_vals) if len(c_vals) > 1 else item.range_min
                c_max = max(c_vals) if len(c_vals) > 1 else item.range_max
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
                if is_serviceable_subset:
                    if not serviceable_population_input:
                        serviceable_population_input = count_ev_input
                elif not population_input or stage_status in ("verified", "VERIFIED"):
                    if population_input and not serviceable_population_input:
                        serviceable_population_input = population_input
                    population_input = count_ev_input
                elif not serviceable_population_input:
                    serviceable_population_input = count_ev_input
            elif unit_norm in ("%", "pct", "percent", "percentage"):
                metric_name_lower = (item.metric or "").lower()
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
                    range_min=item.range_min,
                    range_max=item.range_max,
                )
                if any(k in metric_name_lower for k in ("geo", "geograph", "city", "cities", "urban", "region", "state", "metro", "tier-1", "tier 1")):
                    if not geo_pct_input:
                        geo_pct_input = pct_ev_input
                elif any(k in metric_name_lower for k in ("som", "obtainable", "penetration", "capture", "market share")):
                    if not som_share_input:
                        som_share_input = pct_ev_input
                elif not target_pct_input:
                    target_pct_input = pct_ev_input
            elif resolved_currency is not None or unit_norm in ("usd", "inr", "eur", "gbp", "dollars", "rupees", "crore", "crores", "lakh", "lakhs"):
                metric_name_lower = (item.metric or "").lower()
                metric_type_val = item.metric_type.value if hasattr(item.metric_type, "value") else str(item.metric_type or "")
                
                # Disambiguate between Macro Market Size (for Top-Down) vs Unit Pricing/ARPU (for Bottom-Up)
                is_unit_pricing_metric = (
                    metric_type_val in ("average_price", "annual_spend", "pricing", "arpu", "subscription_price")
                    or any(w in metric_name_lower for w in ("price", "spend", "arpu", "fee", "cost", "subscription", "tuition", "per user", "per student", "per year", "per month", "plan", "rate"))
                    or eff_val < 1_000_000.0
                )
                is_macro_metric = (
                    metric_type_val in ("market_size", "market_revenue")
                    or any(w in metric_name_lower for w in ("market size", "market revenue", "market value", "industry size", "industry revenue", "sector revenue"))
                    or (eff_val >= 1_000_000.0 and not is_unit_pricing_metric)
                )

                c_vals = [s.value for s in getattr(item, "conflicting_sources", []) if getattr(s, "value", None) is not None] + ([eff_val] if eff_val is not None else [])
                c_min = min(c_vals) if len(c_vals) > 1 else item.range_min
                c_max = max(c_vals) if len(c_vals) > 1 else item.range_max

                if is_macro_metric and not is_unit_pricing_metric:
                    if not macro_market_input:
                        macro_market_input = EvidenceInput(
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
                else:
                    if not pricing_input:
                        pricing_input = EvidenceInput(
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
            td_inputs = TopDownCalculationInputs(
                macro_market_size=macro_market_input,
                serviceable_geography_percentage=geo_pct_input,
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
            # Prefer calculated result between bottom-up and top-down
            if calc_report.bottom_up_tam and calc_report.bottom_up_tam.status == CalculationStatus.CALCULATED:
                tam_res = calc_report.bottom_up_tam
            elif calc_report.top_down_tam and calc_report.top_down_tam.status == CalculationStatus.CALCULATED:
                tam_res = calc_report.top_down_tam
            else:
                tam_res = calc_report.bottom_up_tam or calc_report.top_down_tam

            if calc_report.bottom_up_sam and calc_report.bottom_up_sam.status == CalculationStatus.CALCULATED:
                sam_res = calc_report.bottom_up_sam
            elif calc_report.top_down_sam and calc_report.top_down_sam.status == CalculationStatus.CALCULATED:
                sam_res = calc_report.top_down_sam
            else:
                sam_res = calc_report.bottom_up_sam or calc_report.top_down_sam

            if calc_report.bottom_up_som and calc_report.bottom_up_som.status == CalculationStatus.CALCULATED:
                som_res = calc_report.bottom_up_som
            elif calc_report.top_down_som and calc_report.top_down_som.status == CalculationStatus.CALCULATED:
                som_res = calc_report.top_down_som
            else:
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
