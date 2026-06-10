"""Synthetic scenario model."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class SimulationScenario:
    name: str
    description: str
    synthetic_label: str = "synthetic"
    id: str = field(default_factory=lambda: f"scenario-{uuid4()}")
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.synthetic_label != "synthetic":
            raise ValueError("simulation scenarios must be explicitly synthetic")
        if not self.name:
            raise ValueError("scenario name is required")
        if not self.description:
            raise ValueError("scenario description is required")
