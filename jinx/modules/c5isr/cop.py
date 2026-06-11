"""C5ISR COP state management."""

from dataclasses import dataclass, field

from jinx.common.types import DataMode
from jinx.core.schemas import COPState, COPTrack, EntityRef, Event


@dataclass(slots=True)
class COPManager:
    name: str
    data_mode: DataMode = DataMode.SYNTHETIC
    _tracks: dict[str, COPTrack] = field(default_factory=dict)

    def apply_event(self, event: Event, entity: EntityRef | None = None, status: str = "observed") -> None:
        if event.location is None:
            raise ValueError("cannot update COP track without event location")

        track_entity = entity or self._entity_from_event(event)
        self._tracks[track_entity.id] = COPTrack(
            entity=track_entity,
            location=event.location,
            confidence=event.confidence,
            provenance=event.provenance,
            last_report_id=event.metadata.get("operator_report_id", event.id),
            status=status,
            metadata={"source_event_id": event.id},
        )

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

    @staticmethod
    def _entity_from_event(event: Event) -> EntityRef:
        if event.involved_entities:
            return event.involved_entities[0]
        return EntityRef(
            id=event.metadata.get("reporter_id", event.source),
            label=event.metadata.get("reporter_id", event.source),
            entity_type="operator",
        )
