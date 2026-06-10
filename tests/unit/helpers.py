from datetime import UTC, datetime

from jinx.common.types import ConfidenceScore
from jinx.core.provenance import ProvenanceRecord


def confidence() -> ConfidenceScore:
    return ConfidenceScore(
        value=0.72,
        scale="0.0-1.0",
        rationale="Synthetic source is internally consistent but incomplete.",
        source_quality=0.8,
        recency_factor=0.9,
        corroboration_factor=0.7,
        contradiction_factor=0.1,
        completeness_factor=0.6,
    )


def provenance(module: str = "jinx-sim") -> ProvenanceRecord:
    return ProvenanceRecord(
        source="synthetic-feed",
        time_received=datetime.now(UTC),
        processed_by_module=module,
        transformations=("generated", "validated"),
        confidence=confidence(),
    )
