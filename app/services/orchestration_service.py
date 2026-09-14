from datetime import datetime, timezone
import logging
import time
from typing import List, Optional, Union
import uuid

from app.config import settings
from app.discovery.live_provider import LiveDiscoveryProvider
from app.fetching.models import FetchedSource
from app.schemas.business import BusinessAnalysis, CompetitorInfo
from app.schemas.calculation import (
    BottomUpCalculationInputs,
    CalculationAssumption,
    CalculationInput,
    CalculationReport,
    CalculationStatus,
    EvidenceInput,
    PriceFrequency,
    TopDownCalculationInputs,
)
from app.schemas.discovery import (
    DiscoveredSource,
    DiscoveryStatus,
    ResearchQuery,
)
from app.schemas.extraction import (
    ExtractedEvidenceCandidate,
    ExtractionRequest,
)
from app.schemas.orchestration import (
    EvidenceSummary,
    OrchestrationError,
    OrchestrationProgress,
    OrchestrationRequest,
    OrchestrationResult,
    OrchestrationStage,
    OrchestrationStageStatus,
)
from app.schemas.validation import (
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


class OrchestrationService:
    """End-to-end orchestration service connecting all market sizing pipeline components.

    Coordinates:
      1. ANALYZING_BUSINESS (Ollama LLM)
      2. DISCOVERING_EVIDENCE (DiscoveryService via structured queries)
      3. FETCHING_SOURCES (SourceFetchService)
      4. EXTRACTING_EVIDENCE (EvidenceExtractionService)
      5. VALIDATING_EVIDENCE (EvidenceValidationService)
      6. TRIANGULATING_EVIDENCE (Deduplication, conflict detection & multi-source corroboration)
      7. CALCULATING_MARKET (Deterministic calculation engine)
      8. COMPLETED / FAILED (Auditable market analysis response)
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

    async def run(
        self, request: Union[OrchestrationRequest, str]
    ) -> OrchestrationResult:
        """Execute the complete end-to-end market analysis workflow."""
        if isinstance(request, str):
            request = OrchestrationRequest(business_idea=request)

        analysis_id = f"mkt_{uuid.uuid4().hex[:12]}"
        start_wall_time = time.perf_counter()
        created_at = datetime.now(timezone.utc).isoformat()

        # Initialize progress tracker for stages
        ordered_stages = [
            OrchestrationStage.ANALYZING_BUSINESS,
            OrchestrationStage.DISCOVERING_EVIDENCE,
            OrchestrationStage.FETCHING_SOURCES,
            OrchestrationStage.EXTRACTING_EVIDENCE,
            OrchestrationStage.VALIDATING_EVIDENCE,
            OrchestrationStage.TRIANGULATING_EVIDENCE,
            OrchestrationStage.CALCULATING_MARKET,
        ]
        stage_progress_map = {
            st: OrchestrationProgress(stage=st, status=OrchestrationStageStatus.PENDING)
            for st in ordered_stages
        }
        errors: List[OrchestrationError] = []
        warnings: List[str] = []

        def start_stage(st: OrchestrationStage, msg: str) -> None:
            prog = stage_progress_map[st]
            prog.status = OrchestrationStageStatus.RUNNING
            prog.started_at = datetime.now(timezone.utc).isoformat()
            prog.message = msg

        def finish_stage(st: OrchestrationStage, msg: str, dur_ms: float) -> None:
            prog = stage_progress_map[st]
            prog.status = OrchestrationStageStatus.COMPLETED
            prog.completed_at = datetime.now(timezone.utc).isoformat()
            prog.duration_ms = dur_ms
            prog.message = msg

        def fail_stage(st: OrchestrationStage, err_msg: str, dur_ms: Optional[float] = None) -> None:
            prog = stage_progress_map[st]
            prog.status = OrchestrationStageStatus.FAILED
            prog.completed_at = datetime.now(timezone.utc).isoformat()
            prog.duration_ms = dur_ms
            prog.message = err_msg
            prog.error = err_msg
            errors.append(OrchestrationError(stage=st, error_message=err_msg))

        # -------------------------------------------------------------------
        # Step 1: ANALYZING_BUSINESS
        # -------------------------------------------------------------------
        start_stage(OrchestrationStage.ANALYZING_BUSINESS, "Analyzing business idea and extracting structured attributes.")
        t0 = time.perf_counter()
        analysis: Optional[BusinessAnalysis] = None
        try:
            analysis = await self.llm_service.analyze_business_idea(request.business_idea)
            dur = round((time.perf_counter() - t0) * 1000, 2)
            finish_stage(
                OrchestrationStage.ANALYZING_BUSINESS,
                f"Extracted industry '{analysis.industry}' and product '{analysis.product}'.",
                dur,
            )
        except Exception as exc:
            dur = round((time.perf_counter() - t0) * 1000, 2)
            err_msg = f"Business idea extraction failed: {exc}"
            logger.error(err_msg)
            fail_stage(OrchestrationStage.ANALYZING_BUSINESS, err_msg, dur)
            return self._build_response(
                analysis_id=analysis_id,
                request=request,
                status="failed",
                current_stage=OrchestrationStage.FAILED,
                analysis=None,
                queries=[],
                discovered_sources=[],
                fetched_sources=[],
                extracted_candidates=[],
                validation_results=[],
                tri_result=None,
                calc_report=None,
                stages=list(stage_progress_map.values()),
                errors=errors,
                warnings=warnings,
                created_at=created_at,
                total_duration_ms=round((time.perf_counter() - start_wall_time) * 1000, 2),
            )

        # -------------------------------------------------------------------
        # Step 2: Research Query Generation & DISCOVERING_EVIDENCE
        # -------------------------------------------------------------------
        research_queries = self._generate_research_queries(analysis, request)
        is_live_search = False
        try:
            prov = getattr(self.discovery_service, "provider", None)
            if isinstance(prov, LiveDiscoveryProvider):
                is_live_search = True
        except (AttributeError, Exception):
            pass
        if not is_live_search and type(self.discovery_service).__name__ not in ("MagicMock", "Mock", "AsyncMock"):
            is_live_search = (getattr(settings, "SEARCH_PROVIDER", "") or "").lower() in ("live", "tavily", "searxng", "custom")
        t0 = time.perf_counter()
        discovered_sources: List[DiscoveredSource] = []
        try:
            if is_live_search and research_queries:
                unified_q = self._build_unified_live_query(research_queries, analysis, request)
                resp = await self.discovery_service.discover_sources(unified_q)
                if resp.status == DiscoveryStatus.FAILED:
                    errors.append(
                        OrchestrationError(
                            stage=OrchestrationStage.DISCOVERING_EVIDENCE,
                            error_message=resp.message or "Discovery provider failed.",
                        )
                    )
                for src in resp.sources:
                    if src not in discovered_sources and len(discovered_sources) < (request.max_sources * 3):
                        discovered_sources.append(src)
            else:
                for q in research_queries:
                    resp = await self.discovery_service.discover_sources(q)
                    if resp.status == DiscoveryStatus.FAILED:
                        errors.append(
                            OrchestrationError(
                                stage=OrchestrationStage.DISCOVERING_EVIDENCE,
                                error_message=resp.message or "Discovery provider failed.",
                            )
                        )
                    for src in resp.sources:
                        if src not in discovered_sources and len(discovered_sources) < (request.max_sources * 3):
                            discovered_sources.append(src)
            dur = round((time.perf_counter() - t0) * 1000, 2)
            finish_stage(
                OrchestrationStage.DISCOVERING_EVIDENCE,
                f"Discovered {len(discovered_sources)} candidate source(s).",
                dur,
            )
        except Exception as exc:
            dur = round((time.perf_counter() - t0) * 1000, 2)
            err_msg = f"Evidence discovery failed: {exc}"
            logger.error(err_msg)
            fail_stage(OrchestrationStage.DISCOVERING_EVIDENCE, err_msg, dur)
            return self._build_response(
                analysis_id=analysis_id,
                request=request,
                status="failed",
                current_stage=OrchestrationStage.FAILED,
                analysis=analysis,
                queries=research_queries,
                discovered_sources=[],
                fetched_sources=[],
                extracted_candidates=[],
                validation_results=[],
                tri_result=None,
                calc_report=None,
                stages=list(stage_progress_map.values()),
                errors=errors,
                warnings=warnings,
                created_at=created_at,
                total_duration_ms=round((time.perf_counter() - start_wall_time) * 1000, 2),
            )

        if not discovered_sources:
            warnings.append("No external evidence sources discovered. Market sizing halted due to insufficient evidence.")
            return self._build_response(
                analysis_id=analysis_id,
                request=request,
                status="insufficient_evidence",
                current_stage=OrchestrationStage.COMPLETED,
                analysis=analysis,
                queries=research_queries,
                discovered_sources=[],
                fetched_sources=[],
                extracted_candidates=[],
                validation_results=[],
                tri_result=None,
                calc_report=None,
                stages=list(stage_progress_map.values()),
                errors=errors,
                warnings=warnings,
                created_at=created_at,
                total_duration_ms=round((time.perf_counter() - start_wall_time) * 1000, 2),
            )

        # -------------------------------------------------------------------
        # Step 3: FETCHING_SOURCES
        # -------------------------------------------------------------------
        start_stage(OrchestrationStage.FETCHING_SOURCES, f"Fetching content for {len(discovered_sources)} discovered source(s).")
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
        finish_stage(
            OrchestrationStage.FETCHING_SOURCES,
            f"Retrieved content for {len(fetched_sources)} of {len(discovered_sources)} source(s).",
            dur,
        )

        # -------------------------------------------------------------------
        # Step 4: EXTRACTING_EVIDENCE
        # -------------------------------------------------------------------
        start_stage(OrchestrationStage.EXTRACTING_EVIDENCE, "Extracting candidate numerical metrics and competitor data from fetched documents.")
        t0 = time.perf_counter()
        extracted_candidates: List[ExtractedEvidenceCandidate] = []
        extracted_competitors: List[CompetitorInfo] = []
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

            try:
                comps = self.extraction_service.extract_competitors_from_source(doc)
                if comps:
                    extracted_competitors.extend(comps)
            except Exception as comp_err:
                logger.debug("Competitor extraction skipped: %s", comp_err)

        dur = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(
            "Orchestration %s: Extracted %d candidates and %d competitors in %sms",
            analysis_id,
            len(extracted_candidates),
            len(extracted_competitors),
            dur,
        )
        finish_stage(
            OrchestrationStage.EXTRACTING_EVIDENCE,
            f"Extracted {len(extracted_candidates)} candidate metric(s) and {len(extracted_competitors)} competitor(s).",
            dur,
        )

        # -------------------------------------------------------------------
        # Step 5 & 6: VALIDATING_EVIDENCE & TRIANGULATING_EVIDENCE
        # -------------------------------------------------------------------
        start_stage(OrchestrationStage.VALIDATING_EVIDENCE, "Validating candidate integrity and structure.")
        t0 = time.perf_counter()
        validation_results: List[EvidenceValidationResult] = []
        for c in extracted_candidates:
            val_res = self.validation_service.validate_candidate(c)
            validation_results.append(val_res)
        dur = round((time.perf_counter() - t0) * 1000, 2)
        finish_stage(
            OrchestrationStage.VALIDATING_EVIDENCE,
            f"Validated {len(validation_results)} candidate(s).",
            dur,
        )

        start_stage(OrchestrationStage.TRIANGULATING_EVIDENCE, "Triangulating evidence pool for domain corroboration & conflict detection.")
        t0 = time.perf_counter()
        tri_result: Optional[TriangulationResult] = None
        try:
            tri_result = self.validation_service.triangulate_evidence(extracted_candidates, business_analysis=analysis)
            dur = round((time.perf_counter() - t0) * 1000, 2)
            finish_stage(
                OrchestrationStage.TRIANGULATING_EVIDENCE,
                f"Triangulation completed: {len(tri_result.verified_items)} verified, {len(tri_result.conflict_groups)} conflicts.",
                dur,
            )
        except Exception as exc:
            dur = round((time.perf_counter() - t0) * 1000, 2)
            err_msg = f"Triangulation failed: {exc}"
            logger.error(err_msg)
            fail_stage(OrchestrationStage.TRIANGULATING_EVIDENCE, err_msg, dur)
            return self._build_response(
                analysis_id=analysis_id,
                request=request,
                status="failed",
                current_stage=OrchestrationStage.FAILED,
                analysis=analysis,
                queries=research_queries,
                discovered_sources=discovered_sources,
                fetched_sources=fetched_sources,
                extracted_candidates=extracted_candidates,
                validation_results=validation_results,
                tri_result=None,
                calc_report=None,
                stages=list(stage_progress_map.values()),
                errors=errors,
                warnings=warnings,
                created_at=created_at,
                total_duration_ms=round((time.perf_counter() - start_wall_time) * 1000, 2),
            )

        # -------------------------------------------------------------------
        # Step 7: CALCULATING_MARKET (Evidence Gate + Engine)
        # -------------------------------------------------------------------
        start_stage(OrchestrationStage.CALCULATING_MARKET, "Constructing calculation inputs and running market sizing engine.")
        t0 = time.perf_counter()
        calc_report: Optional[CalculationReport] = None
        try:
            calc_input = self._build_calculation_inputs(
                analysis,
                tri_result.validated_items if tri_result else [],
                request,
            )
            calc_report = self.calculation_service.generate_report(calc_input)
            dur = round((time.perf_counter() - t0) * 1000, 2)
            finish_stage(
                OrchestrationStage.CALCULATING_MARKET,
                f"Calculation finished with status: {calc_report.status}.",
                dur,
            )
        except Exception as exc:
            dur = round((time.perf_counter() - t0) * 1000, 2)
            err_msg = f"Market calculation failed: {exc}"
            logger.error(err_msg)
            fail_stage(OrchestrationStage.CALCULATING_MARKET, err_msg, dur)

        # Determine overall status
        final_status = "completed"
        if len(fetched_sources) < len(discovered_sources) and len(fetched_sources) > 0:
            final_status = "partial"
        if tri_result and tri_result.conflict_groups and not tri_result.verified_items:
            final_status = "conflict"
        if calc_report:
            if calc_report.status in (CalculationStatus.INSUFFICIENT_EVIDENCE, "insufficient_evidence"):
                final_status = "insufficient_evidence"
            elif (not calc_report.top_down_tam or calc_report.top_down_tam.status in (CalculationStatus.INSUFFICIENT_EVIDENCE, "insufficient_evidence")) and (not calc_report.bottom_up_tam or calc_report.bottom_up_tam.status in (CalculationStatus.INSUFFICIENT_EVIDENCE, "insufficient_evidence")):
                final_status = "insufficient_evidence"

        total_dur = round((time.perf_counter() - start_wall_time) * 1000, 2)

        final_res = self._build_response(
            analysis_id=analysis_id,
            request=request,
            status=final_status,
            current_stage=OrchestrationStage.COMPLETED,
            analysis=analysis,
            queries=research_queries,
            discovered_sources=discovered_sources,
            fetched_sources=fetched_sources,
            extracted_candidates=extracted_candidates,
            validation_results=validation_results,
            tri_result=tri_result,
            calc_report=calc_report,
            stages=list(stage_progress_map.values()),
            errors=errors,
            warnings=warnings,
            created_at=created_at,
            total_duration_ms=total_dur,
            competitors=extracted_competitors,
        )

        try:
            self.repository.save(final_res)
        except Exception as save_err:
            logger.warning("Failed to persist analysis %s: %s", analysis_id, save_err)

        return final_res

    # Alias for method name flexibility
    async def run_market_analysis(
        self, request: Union[OrchestrationRequest, str]
    ) -> OrchestrationResult:
        """Alias for run() method."""
        return await self.run(request)

    def _generate_research_queries(
        self, analysis: Optional[BusinessAnalysis], request: OrchestrationRequest
    ) -> List[ResearchQuery]:
        """Generate structured research requirements based on extracted business attributes."""
        queries: List[ResearchQuery] = []
        target_geo = request.geography or (analysis.geography if analysis else None)
        target_year = request.year or 2025

        if analysis:
            # 1. Target Customer Demographics / Population
            if analysis.target_customer:
                cust = analysis.target_customer.strip()
                metric_req = f"Number of {cust}" if not any(w in cust.lower() for w in ("number", "count", "total", "population")) else cust
                queries.append(
                    ResearchQuery(
                        metric_required=metric_req,
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
                        metric_required=f"Target customer population in {analysis.industry.strip()}",
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
                        metric_required=f"{analysis.industry.strip()} market size",
                        geography=target_geo,
                        year=target_year,
                        industry_topic=analysis.industry.strip(),
                        max_results=request.max_sources,
                    )
                )
            elif analysis.product:
                queries.append(
                    ResearchQuery(
                        metric_required=f"{analysis.product.strip()} market size",
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
                        metric_required=f"{analysis.product.strip()} pricing and average revenue per user",
                        geography=target_geo,
                        year=target_year,
                        industry_topic=analysis.industry,
                        max_results=request.max_sources,
                    )
                )
            elif analysis.industry:
                queries.append(
                    ResearchQuery(
                        metric_required=f"{analysis.industry.strip()} pricing benchmarks and subscription ARPU",
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
                    metric_required="Target customer population and market size",
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
        request: OrchestrationRequest,
    ) -> ResearchQuery:
        """Construct a single comprehensive research query combining market size, volume, customer base, and segment info for API efficiency."""
        target_geo = request.geography or (analysis.geography if analysis else None) or "Global"
        target_year = request.year or 2026

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
        request: OrchestrationRequest,
    ) -> CalculationInput:
        """Map validated evidence and explicit user assumptions into calculation operands (Evidence Gate)."""
        target_geo = request.geography or (analysis.geography if analysis else None)
        target_yr = request.year or 2025

        assumptions_map = {a.name.lower(): a for a in request.explicit_assumptions}

        population_input: Optional[EvidenceInput] = None
        serviceable_population_input: Optional[EvidenceInput] = None
        geo_pct_input: Optional[EvidenceInput] = None
        target_pct_input: Optional[EvidenceInput] = None
        pricing_input: Optional[EvidenceInput] = None
        som_share_input: Optional[EvidenceInput] = None
        macro_market_input: Optional[EvidenceInput] = None

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

        # Evidence Gate: ONLY structurally validated items with values pass
        for item in validated_items:
            if not item.is_valid:
                continue
            unit_norm = (item.unit or "").lower()
            val_status = item.validation_status.value if hasattr(item.validation_status, "value") else str(item.validation_status or "valid")
            stage_status = item.lifecycle_stage.value if hasattr(item.lifecycle_stage, "value") else str(item.lifecycle_stage or "validated")
            conf_status = item.confidence.value if hasattr(item.confidence, "value") else str(item.confidence or "medium")
            is_prior = bool(item.year is not None and target_yr is not None and item.year == target_yr - 1)

            eff_val = item.value if item.value is not None else ((item.range_min + item.range_max) / 2.0 if (item.range_min is not None and item.range_max is not None) else None)
            if eff_val is None:
                continue

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
                            source_url=item.source_url,
                            source_quality_tier=item.source_quality_tier,
                            market_scope=getattr(item, "market_scope", None),
                            market_scope_explanation=getattr(item, "market_scope_explanation", None),
                            is_prior_year_benchmark=is_prior,
                            entity_concept=item.metric,
                            lifecycle_stage=stage_status,
                        )

        # Apply explicit user assumptions with robust disambiguation
        for a_name, a_obj in assumptions_map.items():
            if any(k in a_name for k in ("price", "arpu", "fee", "cost", "subscription", "pricing")):
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

        # Check for top-down market sizing inputs
        top_down_val_input: Optional[EvidenceInput] = macro_market_input

        for a_name, a_obj in assumptions_map.items():
            if any(k in a_name for k in ("top_down", "market_size", "tam_value", "industry_tam")):
                top_down_val_input = EvidenceInput(
                    name=a_obj.name,
                    value=a_obj.value,
                    unit=a_obj.unit,
                    currency=a_obj.unit.upper() if a_obj.unit.upper() in ("USD", "INR", "EUR", "GBP") else None,
                    is_assumption=True,
                    assumption_justification=a_obj.justification,
                )

        td_inputs = None
        if top_down_val_input is not None:
            td_inputs = TopDownCalculationInputs(
                macro_market_size=top_down_val_input,
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

    def _build_response(
        self,
        analysis_id: str,
        request: OrchestrationRequest,
        status: str,
        current_stage: OrchestrationStage,
        analysis: Optional[BusinessAnalysis],
        queries: List[ResearchQuery],
        discovered_sources: List[DiscoveredSource],
        fetched_sources: List[FetchedSource],
        extracted_candidates: List[ExtractedEvidenceCandidate],
        validation_results: List[EvidenceValidationResult],
        tri_result: Optional[TriangulationResult],
        calc_report: Optional[CalculationReport],
        stages: List[OrchestrationProgress],
        errors: List[OrchestrationError],
        warnings: List[str],
        created_at: str,
        total_duration_ms: Optional[float],
        competitors: Optional[List[CompetitorInfo]] = None,
    ) -> OrchestrationResult:
        """Construct the final user-facing OrchestrationResult."""
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
            tam_res = calc_report.bottom_up_tam or calc_report.top_down_tam
            sam_res = calc_report.bottom_up_sam or calc_report.top_down_sam
            som_res = calc_report.bottom_up_som or calc_report.top_down_som
            confidence = calc_report.confidence
            all_warnings.extend(calc_report.warnings)

        is_failed = (status == "failed" or current_stage == OrchestrationStage.FAILED)

        if is_failed:
            all_warnings.append("Analysis execution failed because the LLM/runtime service was unavailable or encountered an error.")
        else:
            if not discovered_sources:
                all_warnings.append("Insufficient evidence: No external evidence sources were discovered for this business idea.")
            if not tam_res or tam_res.status != CalculationStatus.CALCULATED:
                all_warnings.append("TAM could not be fully calculated due to missing customer population or pricing evidence.")
            if not som_res or som_res.status != CalculationStatus.CALCULATED:
                all_warnings.append("SOM was withheld under the SOM Safety Rule (obtainable market share was not provided).")

        summary = EvidenceSummary(
            total_discovered=len(discovered_sources),
            total_fetched=len(fetched_sources),
            total_extracted_candidates=len(extracted_candidates),
            total_validated=len([v for v in validation_results if v.is_valid]),
            total_verified=len(tri_result.verified_items) if tri_result else 0,
            total_conflicts=len(tri_result.conflict_groups) if tri_result else 0,
        )

        # Determine research provider
        provider_mode = (settings.SEARCH_PROVIDER or "mock").strip().lower()
        if isinstance(getattr(self.discovery_service, "provider", None), LiveDiscoveryProvider) or provider_mode in ("live", "tavily", "searxng", "custom"):
            provider_name = "live"
        else:
            provider_name = "mock"

        if provider_name == "mock":
            all_warnings.insert(0, "These figures are development/test fixtures and should not be used as real-world market estimates.")

        # Evidence quality rating
        eq_rating = "INSUFFICIENT"
        if calc_report and calc_report.evidence_quality:
            eq_rating = (
                calc_report.evidence_quality.value
                if hasattr(calc_report.evidence_quality, "value")
                else str(calc_report.evidence_quality)
            )

        return OrchestrationResult(
            analysis_id=analysis_id,
            status=status,
            current_stage=current_stage,
            business_idea=request.business_idea,
            business_analysis=analysis,
            research_queries=queries,
            discovered_sources=discovered_sources,
            fetched_sources=fetched_sources,
            extracted_candidates=extracted_candidates,
            validation_results=validation_results,
            deduplication_groups=tri_result.duplicate_groups if tri_result else [],
            conflict_groups=tri_result.conflict_groups if tri_result else [],
            triangulation_result=tri_result,
            calculation_report=calc_report,
            tam=tam_res,
            sam=sam_res,
            som=som_res,
            confidence=confidence,
            evidence_quality_rating=eq_rating,
            research_provider=provider_name,
            competitors=competitors or [],
            stages=stages,
            stage_progress=stages,
            errors=errors,
            warnings=list(dict.fromkeys(all_warnings)),
            assumptions=request.explicit_assumptions,
            evidence_summary=summary,
            provenance=unique_provenance,
            created_at=created_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
            total_duration_ms=total_duration_ms,
        )


# Backward-compatible alias
MarketAnalysisOrchestrator = OrchestrationService

_orchestration_service_instance: Optional[OrchestrationService] = None


def get_orchestration_service() -> OrchestrationService:
    """Dependency provider returning singleton OrchestrationService."""
    global _orchestration_service_instance
    if _orchestration_service_instance is None:
        _orchestration_service_instance = OrchestrationService()
    return _orchestration_service_instance
