"""Synthetic scenario model."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Mapping
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class SimulationEvent:
    name: str
    offset_seconds: int
    payload_schema: str
    payload: Mapping[str, object]
    expected_effects: tuple[str, ...] = field(default_factory=tuple)
    id: str = field(default_factory=lambda: f"sim-event-{uuid4()}")

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("simulation event name is required")
        if self.offset_seconds < 0:
            raise ValueError("simulation event offset_seconds must be non-negative")
        if not self.payload_schema:
            raise ValueError("simulation event payload_schema is required")
        if "synthetic" not in self.payload:
            raise ValueError("simulation event payload must declare synthetic status")


@dataclass(frozen=True, slots=True)
class SimulationScenario:
    name: str
    description: str
    synthetic_label: str = "synthetic"
    events: tuple[SimulationEvent, ...] = field(default_factory=tuple)
    id: str = field(default_factory=lambda: f"scenario-{uuid4()}")
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.synthetic_label != "synthetic":
            raise ValueError("simulation scenarios must be explicitly synthetic")
        if not self.name:
            raise ValueError("scenario name is required")
        if not self.description:
            raise ValueError("scenario description is required")

        offsets = [event.offset_seconds for event in self.events]
        if offsets != sorted(offsets):
            raise ValueError("simulation scenario events must be sorted by offset_seconds")
