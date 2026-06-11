"""Bounded context objects for JINX-BRAIN."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Mapping
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class BoundedBrainContext:
    source: str
    allowed_modules: frozenset[str]
    context: Mapping[str, object]
    redactions: tuple[str, ...]
    uncertainty: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    id: str = field(default_factory=lambda: f"brain-context-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("bounded context source is required")
        if not self.allowed_modules:
            raise ValueError("bounded context requires allowed modules")
        if not self.context:
            raise ValueError("bounded context requires context")
