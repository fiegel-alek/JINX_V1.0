"""Core analysis run records and explainability artifacts."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from jinx.common.types import ConfidenceScore


@dataclass(frozen=True, slots=True)
class ConfidenceSummary:
    value: float
    band: str
    rationale: str
    source_quality: float
    recency_factor: float
    corroboration_factor: float
    contradiction_factor: float
    completeness_factor: float
    delta: float = 0.0

    def __post_init__(self) -> None:
        if self.band not in {"low", "medium", "high"}:
            raise ValueError("confidence band must be low, medium, or high")


@dataclass(frozen=True, slots=True)
class ExplanationArtifact:
    output_id: str
    output_type: str
    why_flagged: str
    contributing_inputs: tuple[str, ...]
    brain_references: tuple[str, ...]
    uncertainty: str
    recommended_review_role: str
    allowed_actions: tuple[str, ...]
    disallowed_actions: tuple[str, ...]
    id: str = field(default_factory=lambda: f"explain-{uuid4()}")

    def __post_init__(self) -> None:
        if not self.output_id:
            raise ValueError("explanation output_id is required")
        if not self.why_flagged:
            raise ValueError("explanation why_flagged is required")
        if not self.contributing_inputs:
            raise ValueError("explanation requires contributing inputs")
        if not self.disallowed_actions:
            raise ValueError("explanation requires disallowed actions")


@dataclass(frozen=True, slots=True)
class CoreAnalysisRun:
    input_ids: tuple[str, ...]
    modules_consulted: tuple[str, ...]
    confidence_summary: ConfidenceSummary
    output_ids: tuple[str, ...]
    human_review_required: bool
    id: str = field(default_factory=lambda: f"analysis-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.input_ids:
            raise ValueError("analysis run requires inputs")
        if not self.modules_consulted:
            raise ValueError("analysis run requires consulted modules")
        if not self.human_review_required:
            raise ValueError("core analysis runs require human review")


def confidence_summary_from_score(score: ConfidenceScore, previous_value: float | None = None) -> ConfidenceSummary:
    if score.value < 0.4:
        band = "low"
    elif score.value < 0.75:
        band = "medium"
    else:
        band = "high"
    delta = 0.0 if previous_value is None else round(score.value - previous_value, 2)
    return ConfidenceSummary(
        value=score.value,
        band=band,
        rationale=score.rationale,
        source_quality=score.source_quality,
        recency_factor=score.recency_factor,
        corroboration_factor=score.corroboration_factor,
        contradiction_factor=score.contradiction_factor,
        completeness_factor=score.completeness_factor,
        delta=delta,
    )
