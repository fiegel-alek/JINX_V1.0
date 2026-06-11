"""Simple in-memory stores for audit and provenance records."""

from dataclasses import dataclass, field

from jinx.core.audit import AuditRecord
from jinx.core.provenance import ProvenanceRecord


@dataclass(slots=True)
class AuditRecordStore:
    _records: dict[str, AuditRecord] = field(default_factory=dict)

    def save(self, record: AuditRecord) -> None:
        if record.id in self._records:
            raise ValueError(f"audit record already stored: {record.id}")
        self._records[record.id] = record

    def all(self) -> tuple[AuditRecord, ...]:
        return tuple(self._records.values())

    def by_actor(self, actor: str) -> tuple[AuditRecord, ...]:
        return tuple(record for record in self._records.values() if record.actor == actor)


@dataclass(slots=True)
class ProvenanceRecordStore:
    _records: list[ProvenanceRecord] = field(default_factory=list)

    def save(self, record: ProvenanceRecord) -> None:
        self._records.append(record)

    def all(self) -> tuple[ProvenanceRecord, ...]:
        return tuple(self._records)

    def by_module(self, module_name: str) -> tuple[ProvenanceRecord, ...]:
        return tuple(record for record in self._records if record.processed_by_module == module_name)
