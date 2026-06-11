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
    id: str = field(default_factory=lambda: f"net-issue-{uuid4()}")

    def __post_init__(self) -> None:
        if not self.issue_type:
            raise ValueError("network issue_type is required")
        if not self.summary:
            raise ValueError("network issue summary is required")
        if not self.affected_nodes:
            raise ValueError("network issue requires affected nodes")
