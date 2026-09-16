import json
import logging
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel

from app.storage.database import get_db_connection, init_db

logger = logging.getLogger(__name__)


def _serialize_to_json(val: Any) -> Optional[str]:
    """Safely serialize an object, Pydantic model, or dictionary into a JSON string."""
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if isinstance(val, BaseModel):
        return val.model_dump_json()
    try:
        if isinstance(val, list):
            dumped_list = [item.model_dump() if isinstance(item, BaseModel) else item for item in val]
            return json.dumps(dumped_list)
        if isinstance(val, dict):
            return json.dumps(val)
        return json.dumps(val)
    except Exception as err:
        logger.warning("JSON serialization fallback: %s", err)
        return json.dumps(str(val))


def _deserialize_from_json(val: Optional[str]) -> Any:
    """Safely parse JSON string into Python structure or None."""
    if not val:
        return None
    try:
        return json.loads(val)
    except Exception:
        return val


class AnalysisRepository:
    """Minimal, thread-safe SQLite persistence repository for market analysis runs."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        # Auto-initialize table on instantiation
        try:
            init_db(self.db_path)
        except Exception as exc:
            logger.error("Failed to initialize database: %s", exc)

    def save(self, result: Any) -> str:
        """Persist a PipelineResult or OrchestrationResult into SQLite."""
        if hasattr(result, "pipeline_id"):
            analysis_id = str(result.pipeline_id)
        elif hasattr(result, "analysis_id"):
            analysis_id = str(result.analysis_id)
        elif isinstance(result, dict):
            analysis_id = str(result.get("pipeline_id") or result.get("analysis_id") or "")
        else:
            raise ValueError("Result must have pipeline_id or analysis_id.")

        if not analysis_id:
            raise ValueError("analysis_id cannot be empty.")

        # Extract structured properties
        if isinstance(result, BaseModel):
            result_dict = result.model_dump()
            final_result_json = result.model_dump_json()
        elif isinstance(result, dict):
            result_dict = result
            final_result_json = json.dumps(result)
        else:
            result_dict = getattr(result, "__dict__", {})
            final_result_json = json.dumps(str(result))

        business_idea = str(result_dict.get("business_idea", ""))
        status = str(result_dict.get("status", "completed"))
        confidence = str(result_dict.get("confidence", "low"))
        created_at = str(
            result_dict.get("started_at")
            or result_dict.get("created_at")
            or ""
        )
        completed_at = str(result_dict.get("completed_at") or "")

        conn = get_db_connection(self.db_path)
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO analyses (
                        analysis_id, business_idea, status, confidence, created_at, completed_at,
                        business_analysis, evidence_summary, discovered_sources, fetched_sources,
                        extracted_candidates, validation_results, triangulation_result,
                        calculation_report, tam, sam, som, competitors, assumptions, warnings,
                        errors, final_result
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?,
                        ?, ?
                    )
                    ON CONFLICT(analysis_id) DO UPDATE SET
                        status = excluded.status,
                        confidence = excluded.confidence,
                        completed_at = excluded.completed_at,
                        business_analysis = excluded.business_analysis,
                        evidence_summary = excluded.evidence_summary,
                        discovered_sources = excluded.discovered_sources,
                        fetched_sources = excluded.fetched_sources,
                        extracted_candidates = excluded.extracted_candidates,
                        validation_results = excluded.validation_results,
                        triangulation_result = excluded.triangulation_result,
                        calculation_report = excluded.calculation_report,
                        tam = excluded.tam,
                        sam = excluded.sam,
                        som = excluded.som,
                        competitors = excluded.competitors,
                        assumptions = excluded.assumptions,
                        warnings = excluded.warnings,
                        errors = excluded.errors,
                        final_result = excluded.final_result;
                    """,
                    (
                        analysis_id,
                        business_idea,
                        status,
                        confidence,
                        created_at,
                        completed_at,
                        _serialize_to_json(result_dict.get("business_analysis")),
                        _serialize_to_json(result_dict.get("evidence_summary")),
                        _serialize_to_json(result_dict.get("discovered_sources")),
                        _serialize_to_json(result_dict.get("fetched_sources")),
                        _serialize_to_json(result_dict.get("extracted_candidates")),
                        _serialize_to_json(result_dict.get("validation_results")),
                        _serialize_to_json(result_dict.get("triangulation_result")),
                        _serialize_to_json(result_dict.get("calculation_report")),
                        _serialize_to_json(result_dict.get("tam")),
                        _serialize_to_json(result_dict.get("sam")),
                        _serialize_to_json(result_dict.get("som")),
                        _serialize_to_json(result_dict.get("competitors")),
                        _serialize_to_json(result_dict.get("assumptions")),
                        _serialize_to_json(result_dict.get("warnings")),
                        _serialize_to_json(result_dict.get("errors")),
                        final_result_json,
                    ),
                )
            logger.info("Saved market analysis run [id=%s, status=%s]", analysis_id, status)
            return analysis_id
        finally:
            conn.close()

    def get_by_id(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full market analysis result by ID."""
        conn = get_db_connection(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM analyses WHERE analysis_id = ? LIMIT 1;", (analysis_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            data = dict(row)
            # Parse the final_result JSON string
            if data.get("final_result"):
                parsed = _deserialize_from_json(data["final_result"])
                if isinstance(parsed, dict):
                    if "pipeline_id" not in parsed:
                        parsed["pipeline_id"] = analysis_id
                    if "analysis_id" not in parsed:
                        parsed["analysis_id"] = analysis_id
                    return parsed
            # Fallback to reconstructing from columns
            for k in (
                "business_analysis", "evidence_summary", "discovered_sources",
                "fetched_sources", "extracted_candidates", "validation_results",
                "triangulation_result", "calculation_report", "tam", "sam", "som",
                "competitors", "assumptions", "warnings", "errors"
            ):
                data[k] = _deserialize_from_json(data.get(k))
            return data
        finally:
            conn.close()

    def list_all(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List summary records of previous market analyses ordered by creation date."""
        bounded_limit = max(1, min(limit, 200))
        bounded_offset = max(0, offset)

        conn = get_db_connection(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    analysis_id,
                    business_idea,
                    status,
                    confidence,
                    created_at,
                    completed_at,
                    business_analysis,
                    tam,
                    sam,
                    som
                FROM analyses
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?;
                """,
                (bounded_limit, bounded_offset),
            )
            rows = cur.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["business_analysis"] = _deserialize_from_json(item.get("business_analysis"))
                item["tam"] = _deserialize_from_json(item.get("tam"))
                item["sam"] = _deserialize_from_json(item.get("sam"))
                item["som"] = _deserialize_from_json(item.get("som"))
                results.append(item)
            return results
        finally:
            conn.close()

    def count(self) -> int:
        """Count total stored analyses."""
        conn = get_db_connection(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM analyses;")
            return int(cur.fetchone()[0])
        finally:
            conn.close()

    def delete(self, analysis_id: str) -> bool:
        """Delete an analysis run by ID."""
        conn = get_db_connection(self.db_path)
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM analyses WHERE analysis_id = ?;", (analysis_id,))
                return cur.rowcount > 0
        finally:
            conn.close()

    def clear_all(self) -> None:
        """Clear all stored analyses (for test cleanups)."""
        conn = get_db_connection(self.db_path)
        try:
            with conn:
                conn.execute("DELETE FROM analyses;")
        finally:
            conn.close()


_repository_instance: Optional[AnalysisRepository] = None


def get_repository() -> AnalysisRepository:
    """Dependency provider returning singleton AnalysisRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = AnalysisRepository()
    return _repository_instance
