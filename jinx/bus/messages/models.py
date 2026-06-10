"""Message model for JINX-BUS / JINX-FABRIC."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Mapping
from uuid import uuid4

from jinx.common.types.confidence import ConfidenceScore
from jinx.common.types.enums import DataMode


@dataclass(frozen=True, slots=True)
class FabricMessage:
    source_module: str
    destination: str
    schema_version: str
    sensitivity_label: str
    license_scope: str
    provenance_ref: str
    payload: Mapping[str, object]
    data_mode: DataMode
    confidence: ConfidenceScore | None = None
    simulation_flag: bool = True
    id: str = field(default_factory=lambda: f"msg-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.source_module:
            raise ValueError("message source_module is required")
        if not self.destination:
            raise ValueError("message destination is required")
        if not self.schema_version:
            raise ValueError("message schema_version is required")
        if self.data_mode in {DataMode.SYNTHETIC, DataMode.MOCK} and not self.simulation_flag:
            raise ValueError("synthetic and mock messages must set simulation_flag")
