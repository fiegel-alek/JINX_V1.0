"""Domain-neutral schemas shared across JINX modules."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Mapping
from uuid import uuid4

from jinx.common.types.confidence import ConfidenceScore
from jinx.common.types.enums import (
    AdvisoryLabel,
    DataMode,
    EventType,
    HumanCommandType,
    OperatorReportType,
)
from jinx.core.provenance.models import ProvenanceRecord

PROHIBITED_OPERATOR_ACTION_TERMS = frozenset(
    {
        "autonomous order",
        "authorize strike",
        "control weapon",
        "engage target",
        "fire mission",
        "kill",
        "lethal action",
        "retask collector",
        "targeting decision",
    }
)

PROHIBITED_HUMAN_COMMAND_TERMS = frozenset(
    {
        "authorize strike",
        "control weapon",
        "engage target",
        "fire mission",
        "kill",
        "lethal action",
        "retask collector",
        "targeting decision",
    }
)


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
    potential_human_resolutions: tuple[str, ...]
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
        if not self.likely_impacts:
            raise ValueError("conflict packets require likely impacts")
        if not self.potential_human_resolutions:
            raise ValueError("conflict packets require potential human resolutions")
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
    brain_references: tuple[str, ...] = field(default_factory=tuple)
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


@dataclass(frozen=True, slots=True)
class OperatorReport:
    report_type: OperatorReportType
    reporter_id: str
    source_device_id: str
    summary: str
    confidence: ConfidenceScore
    provenance: ProvenanceRecord
    data_mode: DataMode
    location: Location | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)
    human_originated: bool = True
    requires_human_review: bool = True
    simulation_flag: bool = True
    id: str = field(default_factory=lambda: f"op-report-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.reporter_id:
            raise ValueError("operator report reporter_id is required")
        if not self.source_device_id:
            raise ValueError("operator report source_device_id is required")
        if not self.summary:
            raise ValueError("operator report summary is required")
        if not self.human_originated:
            raise ValueError("operator reports must be human-originated")
        if not self.requires_human_review:
            raise ValueError("operator reports require human review")
        if self.data_mode in {DataMode.SYNTHETIC, DataMode.MOCK} and not self.simulation_flag:
            raise ValueError("synthetic and mock operator reports must be marked as simulation")

        lowered = self.summary.lower()
        for term in PROHIBITED_OPERATOR_ACTION_TERMS:
            if term in lowered:
                raise ValueError(f"operator report contains prohibited action language: {term}")


@dataclass(frozen=True, slots=True)
class COPAdvisory:
    label: AdvisoryLabel
    recipient_id: str
    summary: str
    rationale: str
    confidence: ConfidenceScore
    provenance_chain: tuple[ProvenanceRecord, ...]
    required_human_review: bool
    allowed_actions: tuple[str, ...]
    disallowed_actions: tuple[str, ...]
    affected_entities: tuple[EntityRef, ...] = field(default_factory=tuple)
    related_report_ids: tuple[str, ...] = field(default_factory=tuple)
    id: str = field(default_factory=lambda: f"cop-adv-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.recipient_id:
            raise ValueError("COP advisory recipient_id is required")
        if not self.summary:
            raise ValueError("COP advisory summary is required")
        if not self.rationale:
            raise ValueError("COP advisory rationale is required")
        if not self.provenance_chain:
            raise ValueError("COP advisory requires provenance")
        if not self.required_human_review:
            raise ValueError("COP advisories require human review")
        if not self.allowed_actions:
            raise ValueError("COP advisory must declare allowed actions")
        if not self.disallowed_actions:
            raise ValueError("COP advisory must declare disallowed actions")

        combined = " ".join((self.summary, self.rationale, *self.allowed_actions)).lower()
        for term in PROHIBITED_OPERATOR_ACTION_TERMS:
            if term in combined:
                raise ValueError(f"COP advisory contains prohibited action language: {term}")


@dataclass(frozen=True, slots=True)
class HumanCommandInput:
    command_type: HumanCommandType
    issuing_user_id: str
    issuing_role: str
    text: str
    provenance: ProvenanceRecord
    data_mode: DataMode
    target_module: str
    human_originated: bool = True
    requires_acknowledgement: bool = True
    generated_by_core: bool = False
    simulation_flag: bool = True
    id: str = field(default_factory=lambda: f"human-cmd-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.issuing_user_id:
            raise ValueError("human command issuing_user_id is required")
        if not self.issuing_role:
            raise ValueError("human command issuing_role is required")
        if not self.text:
            raise ValueError("human command text is required")
        if not self.target_module:
            raise ValueError("human command target_module is required")
        if not self.human_originated:
            raise ValueError("commands must be human-originated")
        if self.generated_by_core:
            raise ValueError("JINX-Core must not generate command authority")
        if self.data_mode in {DataMode.SYNTHETIC, DataMode.MOCK} and not self.simulation_flag:
            raise ValueError("synthetic and mock human commands must be marked as simulation")

        lowered = self.text.lower()
        for term in PROHIBITED_HUMAN_COMMAND_TERMS:
            if term in lowered:
                raise ValueError(f"human command contains prohibited action language: {term}")


@dataclass(frozen=True, slots=True)
class COPTrack:
    entity: EntityRef
    location: Location
    confidence: ConfidenceScore
    provenance: ProvenanceRecord
    last_report_id: str
    status: str = "unknown"
    metadata: Mapping[str, str] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.last_report_id:
            raise ValueError("COP track last_report_id is required")
        if not self.status:
            raise ValueError("COP track status is required")


@dataclass(frozen=True, slots=True)
class COPState:
    name: str
    tracks: tuple[COPTrack, ...]
    data_mode: DataMode
    provenance_chain: tuple[ProvenanceRecord, ...]
    simulation_flag: bool = True
    id: str = field(default_factory=lambda: f"cop-state-{uuid4()}")
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("COP state name is required")
        if not self.provenance_chain:
            raise ValueError("COP state requires provenance")
        if self.data_mode in {DataMode.SYNTHETIC, DataMode.MOCK} and not self.simulation_flag:
            raise ValueError("synthetic and mock COP states must be marked as simulation")
