"""Core confidence aggregation for advisory analysis."""

from jinx.common.types import ConfidenceScore
from jinx.core.schemas import Event


class CoreConfidenceEngine:
    def combine_for_conflict(self, events: tuple[Event, ...], rationale: str) -> ConfidenceScore:
        if len(events) < 2:
            raise ValueError("at least two events are required for conflict confidence")

        values = [event.confidence.value for event in events]
        source_quality = sum(event.confidence.source_quality for event in events) / len(events)
        recency_factor = sum(event.confidence.recency_factor for event in events) / len(events)
        completeness_factor = sum(event.confidence.completeness_factor for event in events) / len(events)
        contradiction_factor = max(event.confidence.contradiction_factor for event in events)
        corroboration_factor = min(event.confidence.corroboration_factor for event in events)
        value = max(0.0, min(1.0, (sum(values) / len(values) + contradiction_factor) / 2))

        return ConfidenceScore(
            value=round(value, 2),
            scale="0.0-1.0",
            rationale=rationale,
            source_quality=round(source_quality, 2),
            recency_factor=round(recency_factor, 2),
            corroboration_factor=round(corroboration_factor, 2),
            contradiction_factor=round(contradiction_factor, 2),
            completeness_factor=round(completeness_factor, 2),
            module_specific_notes="Core advisory confidence aggregates approved source confidence.",
        )
