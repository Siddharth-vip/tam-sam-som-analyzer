class PipelineException(Exception):
    """Base exception for all pipeline orchestration errors."""
    pass


class BusinessAnalysisStepException(PipelineException):
    """Raised when the LLM business analysis step fails."""
    pass


class QueryGenerationStepException(PipelineException):
    """Raised when the research query generation step fails."""
    pass


class DiscoveryStepException(PipelineException):
    """Raised when the evidence discovery step fails."""
    pass


class FetchingStepException(PipelineException):
    """Raised when source fetching fails."""
    pass


class ExtractionStepException(PipelineException):
    """Raised when candidate evidence extraction fails."""
    pass


class ValidationStepException(PipelineException):
    """Raised when validation or triangulation fails."""
    pass


class CalculationStepException(PipelineException):
    """Raised when market sizing calculation fails."""
    pass
