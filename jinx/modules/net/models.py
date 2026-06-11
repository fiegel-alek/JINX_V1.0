"""JINX-NET synthetic MTDL network models."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from jinx.common.types import ConfidenceScore, DataMode
from jinx.core.provenance import ProvenanceRecord


@dataclass(frozen=True, slots=True)
class NetworkNode:
    id: str
    label: str
    node_type: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("network node id is required")
        if not self.label:
            raise ValueError("network node label is required")
        if not self.node_type:
            raise ValueError("network node type is required")


@dataclass(frozen=True, slots=True)
class TimeslotAllocation:
    slot_id: str
    node_id: str
    epoch: str
    purpose: str = "synthetic_mtdl"

    def __post_init__(self) -> None:
        if not self.slot_id:
            raise ValueError("timeslot allocation slot_id is required")
        if not self.node_id:
            raise ValueError("timeslot allocation node_id is required")
        if not self.epoch:
            raise ValueError("timeslot allocation epoch is required")


@dataclass(frozen=True, slots=True)
class LOSLink:
    from_node: str
    to_node: str
    status: str
    rationale: str

    def __post_init__(self) -> None:
        if not self.from_node or not self.to_node:
            raise ValueError("LOS link requires from_node and to_node")
        if self.status not in {"clear", "degraded", "blocked", "unknown"}:
            raise ValueError("invalid LOS link status")
        if not self.rationale:
            raise ValueError("LOS link rationale is required")


@dataclass(frozen=True, slots=True)
class NetworkPlan:
    name: str
    nodes: tuple[NetworkNode, ...]
    timeslots: tuple[TimeslotAllocation, ...]
    los_links: tuple[LOSLink, ...]
    confidence: ConfidenceScore
    provenance: ProvenanceRecord
    data_mode: DataMode
    source_format: str = "synthetic_net_plan"
    simulation_flag: bool = True
    id: str = field(default_factory=lambda: f"net-plan-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("network plan name is required")
        if not self.nodes:
            raise ValueError("network plan requires nodes")
        if self.data_mode in {DataMode.SYNTHETIC, DataMode.MOCK} and not self.simulation_flag:
            raise ValueError("synthetic and mock network plans must be marked as simulation")


@dataclass(frozen=True, slots=True)
class NetworkStatus:
    name: str
    nodes: tuple[NetworkNode, ...]
    timeslot_conflicts: tuple[str, ...]
    los_warnings: tuple[str, ...]
    confidence: ConfidenceScore
    provenance: ProvenanceRecord
    data_mode: DataMode
    simulation_flag: bool = True
    id: str = field(default_factory=lambda: f"net-status-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("network status name is required")
        if not self.nodes:
            raise ValueError("network status requires at least one node")
        if self.data_mode in {DataMode.SYNTHETIC, DataMode.MOCK} and not self.simulation_flag:
            raise ValueError("synthetic and mock network status must be marked as simulation")


@dataclass(frozen=True, slots=True)
class NetworkIssue:
    issue_type: str
    summary: str
    affected_nodes: tuple[str, ...]
    confidence: ConfidenceScore
    provenance: ProvenanceRecord
    recommended_review_role: str = "network manager"
    severity: str = "medium"
    recommended_human_actions: tuple[str, ...] = (
        "Review synthetic NET issue details.",
        "Compare timing, geometry, and configuration assumptions.",
    )
    disallowed_actions: tuple[str, ...] = (
        "Do not modify live network configuration from this advisory.",
        "Do not control radios or physical effects.",
    )
    id: str = field(default_factory=lambda: f"net-issue-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.issue_type:
            raise ValueError("network issue_type is required")
        if not self.summary:
            raise ValueError("network issue summary is required")
        if not self.affected_nodes:
            raise ValueError("network issue requires affected nodes")
        if self.severity not in {"low", "medium", "high"}:
            raise ValueError("network issue severity must be low, medium, or high")
        if not self.recommended_human_actions:
            raise ValueError("network issue requires recommended human actions")
        if not self.disallowed_actions:
            raise ValueError("network issue requires disallowed actions")


@dataclass(frozen=True, slots=True)
class NetworkValidationRun:
    plan_id: str
    issue_ids: tuple[str, ...]
    confidence: ConfidenceScore
    summary: str
    id: str = field(default_factory=lambda: f"net-validation-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.plan_id:
            raise ValueError("network validation run plan_id is required")
        if not self.summary:
            raise ValueError("network validation run summary is required")
