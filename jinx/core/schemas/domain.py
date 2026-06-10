"""Domain-neutral schemas shared across JINX modules."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Mapping
from uuid import uuid4

from jinx.common.types.confidence import ConfidenceScore
from jinx.common.types.enums import DataMode, EventType
from jinx.core.provenance.models import ProvenanceRecord


@dataclass(frozen=True, slots=True)
class Location:
    label: str
    latitude: float | None = None
    longitude: float | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("location label is required")
        if self.latitude is not None and not -90.0 <= self.latitude <= 90.0:
            raise ValueError("latitude must be between -90.0 and 90.0")
        if self.longitude is not None and not -180.0 <= self.longitude <= 180.0:
            raise ValueError("longitude must be between -180.0 and 180.0")


@dataclass(frozen=True, slots=True)
class EntityRef:
    id: str
    label: str
    entity_type: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("entity id is required")
        if not self.label:
            raise ValueError("entity label is required")
        if not self.entity_type:
            raise ValueError("entity_type is required")


@dataclass(frozen=True, slots=True)
class Event:
    event_type: EventType
    source: str
    description: str
    confidence: ConfidenceScore
    provenance: ProvenanceRecord
    data_mode: DataMode
    location: Location | None = None
    involved_entities: tuple[EntityRef, ...] = field(default_factory=tuple)
    metadata: Mapping[str, str] = field(default_factory=dict)
    simulation_flag: bool = True
    id: str = field(default_factory=lambda: f"event-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("event source is required")
        if not self.description:
            raise ValueError("event description is required")
        if self.data_mode in {DataMode.SYNTHETIC, DataMode.MOCK} and not self.simulation_flag:
            raise ValueError("synthetic and mock events must be marked as simulation")


@dataclass(frozen=True, slots=True)
class ConflictPacket:
    conflict_type: str
    detected_by_module: str
    conflicting_items: tuple[str, ...]
    likely_impacts: tuple[str, ...]
    confidence: ConfidenceScore
    explanation: str
    recommended_review_role: str
    provenance_chain: tuple[ProvenanceRecord, ...]
    simulation_replay_available: bool = False
    id: str = field(default_factory=lambda: f"conflict-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.conflict_type:
            raise ValueError("conflict_type is required")
        if not self.detected_by_module:
            raise ValueError("detected_by_module is required")
        if len(self.conflicting_items) < 2:
            raise ValueError("conflict packets require at least two conflicting items")
        if not self.explanation:
            raise ValueError("conflict explanation is required")
        if not self.recommended_review_role:
            raise ValueError("recommended_review_role is required")
        if not self.provenance_chain:
            raise ValueError("conflict packets require provenance")


@dataclass(frozen=True, slots=True)
class Recommendation:
    recommendation_type: str
    text: str
    rationale: str
    assumptions: tuple[str, ...]
    risks: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    confidence: ConfidenceScore
    required_human_review: bool
    allowed_actions: tuple[str, ...]
    disallowed_actions: tuple[str, ...]
    provenance_chain: tuple[ProvenanceRecord, ...]
    id: str = field(default_factory=lambda: f"rec-{uuid4()}")

    def __post_init__(self) -> None:
        if not self.recommendation_type:
            raise ValueError("recommendation_type is required")
        if not self.text:
            raise ValueError("recommendation text is required")
        if not self.rationale:
            raise ValueError("recommendation rationale is required")
        if not self.required_human_review:
            raise ValueError("recommendations require human review")
        if not self.allowed_actions:
            raise ValueError("recommendations must declare allowed actions")
        if not self.disallowed_actions:
            raise ValueError("recommendations must declare disallowed actions")
        if not self.provenance_chain:
            raise ValueError("recommendations require provenance")
