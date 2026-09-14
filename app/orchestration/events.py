from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional
from app.orchestration.models import (
    PipelineProgressEvent,
    PipelineStage,
    PipelineStatus,
)


def create_progress_event(
    pipeline_id: str,
    stage: PipelineStage,
    status: PipelineStatus,
    message: str,
    progress_percent: int,
    metadata: Optional[Dict[str, Any]] = None,
) -> PipelineProgressEvent:
    """Create a structured pipeline progress event."""
    return PipelineProgressEvent(
        pipeline_id=pipeline_id,
        stage=stage,
        status=status,
        message=message,
        progress_percent=progress_percent,
        timestamp=datetime.now(timezone.utc).isoformat(),
        metadata=metadata or {},
    )


def format_sse_event(event: PipelineProgressEvent) -> str:
    """Format a PipelineProgressEvent into a standard Server-Sent Events (SSE) data frame."""
    return f"data: {event.model_dump_json()}\n\n"
