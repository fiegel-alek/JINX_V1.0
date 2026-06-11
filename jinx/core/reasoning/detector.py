"""Core advisory conflict detection."""

from jinx.common.types import EventType
from jinx.core.reasoning.confidence import CoreConfidenceEngine
from jinx.core.reasoning.explanation import CoreExplanationEngine
from jinx.core.schemas import ConflictPacket, Event


class CoreConflictDetector:
    def __init__(
        self,
        confidence_engine: CoreConfidenceEngine | None = None,
        explanation_engine: CoreExplanationEngine | None = None,
    ) -> None:
        self._confidence_engine = confidence_engine or CoreConfidenceEngine()
        self._explanation_engine = explanation_engine or CoreExplanationEngine()

    def detect(self, events: tuple[Event, ...]) -> tuple[ConflictPacket, ...]:
        communications_conflict = self._detect_communications_status_conflict(events)
        if communications_conflict is None:
            return ()
        return (communications_conflict,)

    def _detect_communications_status_conflict(
        self, events: tuple[Event, ...]
    ) -> ConflictPacket | None:
        available = self._first_event_with_status(events, "available")
        unavailable = self._first_event_with_status(events, "unavailable")
        if available is None or unavailable is None:
            return None

        confidence = self._confidence_engine.combine_for_conflict(
            (available, unavailable),
            rationale="Synthetic communications availability reports contradict each other.",
        )
        return ConflictPacket(
            conflict_type="communications_status_conflict",
            detected_by_module="jinx-core",
            conflicting_items=(available.id, unavailable.id),
            likely_impacts=(
                "COP communications status confidence reduced",
                "JINX-NET review may be useful if the module is licensed",
                "Simulation replay recommended before further planning assumptions are used",
            ),
            confidence=confidence,
            explanation=self._explanation_engine.communications_conflict(available, unavailable),
            recommended_review_role="network manager",
            provenance_chain=(available.provenance, unavailable.provenance),
            simulation_replay_available=True,
        )

    @staticmethod
    def _first_event_with_status(events: tuple[Event, ...], status: str) -> Event | None:
        for event in events:
            if event.metadata.get("communications_status") == status:
                return event
            if status == "available" and event.event_type == EventType.COMMUNICATIONS_AVAILABLE:
                return event
            if status == "unavailable" and event.event_type == EventType.COMMUNICATIONS_LOSS:
                return event
        return None
