"""Simulation-first message intake and topology models for JINX-Integrator."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from jinx.common.types import ConfidenceScore, DataMode
from jinx.core.provenance import ProvenanceRecord

SUPPORTED_MESSAGE_FAMILIES = frozenset({"vmf", "k-series", "j-series", "usmtf"})
SUPPORTED_TOPOLOGY_KINDS = frozenset({"jinx_architecture", "optasklink_network"})


@dataclass(frozen=True, slots=True)
class MessageFilterProfile:
    family: str
    route_targets: tuple[str, ...]
    required_fields: tuple[str, ...]
    summary: str
    filter_actions: tuple[str, ...]
    restrictions: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.family not in SUPPORTED_MESSAGE_FAMILIES:
            raise ValueError("unsupported integrator message family")
        if not self.route_targets:
            raise ValueError("filter profile route_targets are required")
        if not self.required_fields:
            raise ValueError("filter profile required_fields are required")
        if not self.filter_actions:
            raise ValueError("filter profile filter_actions are required")
        if not self.restrictions:
            raise ValueError("filter profile restrictions are required")


@dataclass(frozen=True, slots=True)
class IntegratorIntakeMessage:
    message_family: str
    message_type: str
    originator: str
    recipient: str
    summary: str
    raw_text: str
    transport: str
    precedence: str
    confidence: ConfidenceScore
    provenance: ProvenanceRecord
    data_mode: DataMode
    restrictions: tuple[str, ...]
    route_targets: tuple[str, ...]
    filter_profile: str
    network_scope: str = "fabric-shadow"
    tags: tuple[str, ...] = ()
    simulation_flag: bool = True
    id: str = field(default_factory=lambda: f"integrator-msg-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.message_family not in SUPPORTED_MESSAGE_FAMILIES:
            raise ValueError("unsupported integrator message family")
        if not self.message_type:
            raise ValueError("integrator message_type is required")
        if not self.originator:
            raise ValueError("integrator originator is required")
        if not self.recipient:
            raise ValueError("integrator recipient is required")
        if not self.summary:
            raise ValueError("integrator summary is required")
        if not self.raw_text.strip():
            raise ValueError("integrator raw_text is required")
        if not self.transport:
            raise ValueError("integrator transport is required")
        if not self.precedence:
            raise ValueError("integrator precedence is required")
        if not self.restrictions:
            raise ValueError("integrator restrictions are required")
        if not self.route_targets:
            raise ValueError("integrator route_targets are required")
        if self.data_mode in {DataMode.SYNTHETIC, DataMode.MOCK} and not self.simulation_flag:
            raise ValueError("synthetic integrator messages must be marked as simulation")


@dataclass(frozen=True, slots=True)
class IntegratorParseResult:
    intake: IntegratorIntakeMessage
    normalized_payload: dict[str, object]
    extracted_fields: dict[str, str]
    validation_notes: tuple[str, ...]
    filter_actions: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.normalized_payload:
            raise ValueError("integrator normalized_payload is required")
        if not self.filter_actions:
            raise ValueError("integrator filter_actions are required")


@dataclass(frozen=True, slots=True)
class IntegratorTopologyNode:
    id: str
    label: str
    node_type: str
    domain: str
    x: float
    y: float
    status: str = "planned"
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("integrator topology node id is required")
        if not self.label:
            raise ValueError("integrator topology node label is required")
        if not self.node_type:
            raise ValueError("integrator topology node type is required")
        if not self.domain:
            raise ValueError("integrator topology node domain is required")
        if not 0 <= self.x <= 1:
            raise ValueError("integrator topology node x must be between 0 and 1")
        if not 0 <= self.y <= 1:
            raise ValueError("integrator topology node y must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class IntegratorTopologyLink:
    id: str
    source: str
    target: str
    link_type: str
    status: str
    summary: str
    payloads: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("integrator topology link id is required")
        if not self.source:
            raise ValueError("integrator topology link source is required")
        if not self.target:
            raise ValueError("integrator topology link target is required")
        if not self.link_type:
            raise ValueError("integrator topology link type is required")
        if not self.status:
            raise ValueError("integrator topology link status is required")
        if not self.summary:
            raise ValueError("integrator topology link summary is required")


@dataclass(frozen=True, slots=True)
class IntegratorTopologyDesign:
    name: str
    summary: str
    design_kind: str
    nodes: tuple[IntegratorTopologyNode, ...]
    links: tuple[IntegratorTopologyLink, ...]
    source_reference: str = ""
    simulation_flag: bool = True
    id: str = field(default_factory=lambda: f"integrator-topology-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("integrator topology name is required")
        if not self.summary:
            raise ValueError("integrator topology summary is required")
        if self.design_kind not in SUPPORTED_TOPOLOGY_KINDS:
            raise ValueError("unsupported integrator topology kind")
        if not self.nodes:
            raise ValueError("integrator topology requires nodes")
        if not self.links:
            raise ValueError("integrator topology requires links")
