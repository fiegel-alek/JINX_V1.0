"""JINX-INTEL fusion models for authorized or synthetic summaries."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from jinx.common.types import ConfidenceScore, DataMode
from jinx.core.provenance import ProvenanceRecord


@dataclass(frozen=True, slots=True)
class IntelligenceSummary:
    source_category: str
    summary: str
    reliability: float
    confidence: ConfidenceScore
    provenance: ProvenanceRecord
    data_mode: DataMode
    restrictions: tuple[str, ...]
    related_entities: tuple[str, ...] = ()
    related_locations: tuple[str, ...] = ()
    simulation_flag: bool = True
    id: str = field(default_factory=lambda: f"intel-summary-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.source_category:
            raise ValueError("intelligence summary source_category is required")
        if not self.summary:
            raise ValueError("intelligence summary text is required")
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError("intelligence summary reliability must be between 0.0 and 1.0")
        if not self.restrictions:
            raise ValueError("intelligence summary restrictions are required")
        if self.data_mode in {DataMode.SYNTHETIC, DataMode.MOCK} and not self.simulation_flag:
            raise ValueError("synthetic and mock intelligence summaries must be marked as simulation")


@dataclass(frozen=True, slots=True)
class IntelligenceImpact:
    impacted_area: str
    summary: str
    confidence: ConfidenceScore
    provenance: ProvenanceRecord
    id: str = field(default_factory=lambda: f"intel-impact-{uuid4()}")

    def __post_init__(self) -> None:
        if not self.impacted_area:
            raise ValueError("intelligence impact impacted_area is required")
        if not self.summary:
            raise ValueError("intelligence impact summary is required")


@dataclass(frozen=True, slots=True)
class IntelligenceFusionResult:
    summaries: tuple[IntelligenceSummary, ...]
    impacts: tuple[IntelligenceImpact, ...]
    id: str = field(default_factory=lambda: f"intel-fusion-{uuid4()}")

    def __post_init__(self) -> None:
        if not self.summaries:
            raise ValueError("intelligence fusion requires summaries")


@dataclass(frozen=True, slots=True)
class ISRFeedSnapshot:
    feed_name: str
    feed_type: str
    status: str
    coverage_area: str
    summary: str
    confidence: ConfidenceScore
    provenance: ProvenanceRecord
    data_mode: DataMode
    restrictions: tuple[str, ...]
    related_entities: tuple[str, ...] = ()
    related_locations: tuple[str, ...] = ()
    simulation_flag: bool = True
    id: str = field(default_factory=lambda: f"isr-feed-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.feed_name:
            raise ValueError("ISR feed name is required")
        if not self.feed_type:
            raise ValueError("ISR feed type is required")
        if not self.status:
            raise ValueError("ISR feed status is required")
        if not self.coverage_area:
            raise ValueError("ISR feed coverage_area is required")
        if not self.summary:
            raise ValueError("ISR feed summary is required")
        if not self.restrictions:
            raise ValueError("ISR feed restrictions are required")
        if self.data_mode in {DataMode.SYNTHETIC, DataMode.MOCK} and not self.simulation_flag:
            raise ValueError("synthetic and mock ISR feed snapshots must be marked as simulation")
