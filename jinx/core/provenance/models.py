"""Provenance records for important facts and outputs."""

from dataclasses import dataclass, field
from datetime import datetime

from jinx.common.types.confidence import ConfidenceScore


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    source: str
    time_received: datetime
    processed_by_module: str
    transformations: tuple[str, ...]
    confidence: ConfidenceScore
    user_interactions: tuple[str, ...] = field(default_factory=tuple)
    downstream_outputs: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("provenance source is required")
        if not self.processed_by_module:
            raise ValueError("processed_by_module is required")
