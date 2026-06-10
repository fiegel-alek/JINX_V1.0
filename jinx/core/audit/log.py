"""Append-only audit records."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Mapping
from uuid import uuid4

from jinx.common.types.enums import AuditEventType


@dataclass(frozen=True, slots=True)
class AuditRecord:
    event_type: AuditEventType
    actor: str
    summary: str
    metadata: Mapping[str, str]
    id: str = field(default_factory=lambda: f"audit-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.actor:
            raise ValueError("audit actor is required")
        if not self.summary:
            raise ValueError("audit summary is required")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(slots=True)
class AuditLog:
    _records: list[AuditRecord] = field(default_factory=list)

    def append(self, record: AuditRecord) -> None:
        self._records.append(record)

    def records(self) -> tuple[AuditRecord, ...]:
        return tuple(self._records)
