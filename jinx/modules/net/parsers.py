"""Synthetic parser stubs for JINX-NET."""

from jinx.common.types import ConfidenceScore, DataMode
from jinx.core.provenance import ProvenanceRecord
from jinx.modules.net.models import LOSLink, NetworkNode, NetworkPlan, TimeslotAllocation


class SyntheticNetworkPlanParser:
    def parse(
        self,
        text: str,
        confidence: ConfidenceScore,
        provenance: ProvenanceRecord,
        data_mode: DataMode = DataMode.SYNTHETIC,
        source_format: str = "synthetic_optasklink_stub",
    ) -> NetworkPlan:
        if not text.strip():
            raise ValueError("synthetic network plan text is required")

        nodes: list[NetworkNode] = []
        timeslots: list[TimeslotAllocation] = []
        los_links: list[LOSLink] = []
        name = "Synthetic NET Plan"

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if key == "name":
                name = value
            elif key == "node":
                node_id, label, node_type = self._split(value, 3)
                nodes.append(NetworkNode(node_id, label, node_type))
            elif key == "slot":
                slot_id, node_id, epoch = self._split(value, 3)
                timeslots.append(TimeslotAllocation(slot_id, node_id, epoch))
            elif key == "los":
                from_node, to_node, status, rationale = self._split(value, 4)
                los_links.append(LOSLink(from_node, to_node, status, rationale))

        if not nodes:
            raise ValueError("synthetic network plan text requires at least one node line")

        return NetworkPlan(
            name=name,
            nodes=tuple(nodes),
            timeslots=tuple(timeslots),
            los_links=tuple(los_links),
            confidence=confidence,
            provenance=provenance,
            data_mode=data_mode,
            source_format=source_format,
        )

    @staticmethod
    def _split(value: str, count: int) -> tuple[str, ...]:
        parts = tuple(part.strip() for part in value.split(","))
        if len(parts) != count or any(not part for part in parts):
            raise ValueError(f"expected {count} comma-separated fields")
        return parts
