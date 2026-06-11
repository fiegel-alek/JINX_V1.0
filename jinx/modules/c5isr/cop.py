"""C5ISR COP state management."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from jinx.common.types import DataMode
from jinx.core.schemas import COPState, COPTrack, EntityRef, Event


@dataclass(slots=True)
class COPManager:
    name: str
    data_mode: DataMode = DataMode.SYNTHETIC
    stale_after: timedelta = timedelta(minutes=30)
    _tracks: dict[str, COPTrack] = field(default_factory=dict)
    _history: dict[str, list[dict[str, str]]] = field(default_factory=dict)

    def apply_event(self, event: Event, entity: EntityRef | None = None, status: str = "active") -> None:
        if event.location is None:
            raise ValueError("cannot update COP track without event location")

        track_entity = entity or self._entity_from_event(event)
        previous = self._tracks.get(track_entity.id)
        lifecycle = self._lifecycle_for_event(event, previous)
        history = self._history.setdefault(track_entity.id, [])
        history.append(
            {
                "event_id": event.id,
                "report_id": event.metadata.get("operator_report_id", event.id),
                "location": event.location.label,
                "status": status,
                "lifecycle": lifecycle,
                "timestamp": event.timestamp.isoformat(),
            }
        )
        self._tracks[track_entity.id] = COPTrack(
            entity=track_entity,
            location=event.location,
            confidence=event.confidence,
            provenance=event.provenance,
            last_report_id=event.metadata.get("operator_report_id", event.id),
            status=status,
            metadata={
                "source_event_id": event.id,
                "lifecycle": lifecycle,
                "history_count": str(len(history)),
                "human_validated": str(False),
            },
        )

    def validate_track(self, entity_id: str, reviewer_id: str, note: str = "") -> COPTrack:
        if entity_id not in self._tracks:
            raise KeyError(f"COP track not found: {entity_id}")
        track = self._tracks[entity_id]
        metadata = dict(track.metadata)
        metadata["lifecycle"] = "human_validated"
        metadata["human_validated"] = str(True)
        metadata["validated_by"] = reviewer_id
        metadata["validation_note"] = note
        self._tracks[entity_id] = COPTrack(
            entity=track.entity,
            location=track.location,
            confidence=track.confidence,
            provenance=track.provenance,
            last_report_id=track.last_report_id,
            status="human_validated",
            metadata=metadata,
            updated_at=datetime.now(UTC),
        )
        self._history.setdefault(entity_id, []).append(
            {
                "event_id": "human-track-validation",
                "report_id": track.last_report_id,
                "location": track.location.label,
                "status": "human_validated",
                "lifecycle": "human_validated",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        return self._tracks[entity_id]

    def track_history(self, entity_id: str) -> tuple[dict[str, str], ...]:
        return tuple(self._history.get(entity_id, ()))

    def state(self) -> COPState:
        if not self._tracks:
            raise ValueError("cannot build COP state without tracks")
        provenance_chain = tuple(track.provenance for track in self._tracks.values())
        return COPState(
            name=self.name,
            tracks=tuple(self._tracks.values()),
            data_mode=self.data_mode,
            provenance_chain=provenance_chain,
        )

    def _lifecycle_for_event(self, event: Event, previous: COPTrack | None) -> str:
        if previous is None:
            return "new"
        if previous.location.label != event.location.label:
            return "conflicting"
        if datetime.now(UTC) - previous.updated_at > self.stale_after:
            return "stale"
        return "active"

    @staticmethod
    def _entity_from_event(event: Event) -> EntityRef:
        if event.involved_entities:
            return event.involved_entities[0]
        return EntityRef(
            id=event.metadata.get("reporter_id", event.source),
            label=event.metadata.get("reporter_id", event.source),
            entity_type="operator",
        )
