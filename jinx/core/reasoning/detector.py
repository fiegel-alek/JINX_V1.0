"""Core advisory conflict detection."""

from collections import defaultdict

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
        conflicts: list[ConflictPacket] = []
        for detector in (
            self._detect_communications_status_conflict,
            self._detect_cop_location_conflict,
            self._detect_cop_status_conflict,
            self._detect_operator_intel_mission_impact_conflict,
        ):
            conflict = detector(events)
            if conflict is not None:
                conflicts.append(conflict)
        return tuple(conflicts)

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
            potential_human_resolutions=(
                "Request human review from the network manager or C5ISR manager.",
                "Run a synthetic replay before relying on communications availability.",
                "Annotate the affected COP track or planning assumption as confidence-limited.",
            ),
            confidence=confidence,
            explanation=self._explanation_engine.communications_conflict(available, unavailable),
            recommended_review_role="network manager",
            provenance_chain=(available.provenance, unavailable.provenance),
            simulation_replay_available=True,
        )

    def _detect_cop_location_conflict(self, events: tuple[Event, ...]) -> ConflictPacket | None:
        by_actor: dict[str, list[Event]] = defaultdict(list)
        for event in events:
            if event.location is None:
                continue
            actor = event.metadata.get("reporter_id") or event.source
            if event.event_type in {EventType.POSITION_UPDATE, EventType.STATUS_UPDATE, EventType.HAZARD}:
                by_actor[actor].append(event)

        for actor, actor_events in by_actor.items():
            locations = {event.location.label for event in actor_events if event.location is not None}
            if len(locations) < 2:
                continue
            first = actor_events[0]
            second = next(
                event
                for event in actor_events[1:]
                if event.location is not None
                and first.location is not None
                and event.location.label != first.location.label
            )
            selected = (first, second)
            confidence = self._confidence_engine.combine_for_conflict(
                selected,
                rationale="Synthetic COP inputs report different locations for the same actor.",
            )
            return ConflictPacket(
                conflict_type="cop_location_conflict",
                detected_by_module="jinx-core",
                conflicting_items=tuple(event.id for event in selected),
                likely_impacts=(
                    "COP track location confidence reduced",
                    "Mission timing assumptions may need review",
                    "Operator confirmation may be required before updating the displayed track",
                ),
                potential_human_resolutions=(
                    "Ask the C5ISR manager to compare report timestamps and provenance.",
                    "Request a human-originated clarification from the affected operator if appropriate.",
                    "Keep both locations visible as confidence-limited until a reviewer validates one.",
                ),
                confidence=confidence,
                explanation=(
                    f"Synthetic COP location conflict detected for {actor}: approved inputs reference "
                    f"different locations ({', '.join(sorted(locations))}). JINX-Core preserves both "
                    "claims and requires human review."
                ),
                recommended_review_role="c5isr manager",
                provenance_chain=tuple(event.provenance for event in selected),
                simulation_replay_available=True,
            )
        return None

    def _detect_cop_status_conflict(self, events: tuple[Event, ...]) -> ConflictPacket | None:
        by_actor: dict[str, list[Event]] = defaultdict(list)
        for event in events:
            if event.event_type in {
                EventType.COMMUNICATIONS_AVAILABLE,
                EventType.COMMUNICATIONS_CHECK,
                EventType.COMMUNICATIONS_LOSS,
            }:
                continue
            actor = event.metadata.get("reporter_id") or event.source
            status = self._status_claim(event)
            if status is not None:
                by_actor[actor].append(event)

        for actor, actor_events in by_actor.items():
            statuses = {self._status_claim(event) for event in actor_events}
            if "available" not in statuses or "unavailable" not in statuses:
                continue
            available = next(event for event in actor_events if self._status_claim(event) == "available")
            unavailable = next(event for event in actor_events if self._status_claim(event) == "unavailable")
            selected = (available, unavailable)
            confidence = self._confidence_engine.combine_for_conflict(
                selected,
                rationale="Synthetic C5ISR status claims contradict each other.",
            )
            return ConflictPacket(
                conflict_type="cop_status_conflict",
                detected_by_module="jinx-core",
                conflicting_items=tuple(event.id for event in selected),
                likely_impacts=(
                    "Track status should remain confidence-limited",
                    "Mission assumptions depending on that status may need review",
                    "C5ISR review queue should preserve both reports",
                ),
                potential_human_resolutions=(
                    "Ask the C5ISR manager to validate the latest human-originated status.",
                    "Compare source recency, confidence, and completeness before updating the track.",
                    "Record a reviewer note explaining why one status was accepted or deferred.",
                ),
                confidence=confidence,
                explanation=(
                    f"Synthetic status conflict detected for {actor}: one approved input indicates "
                    "availability while another indicates unavailability. JINX-Core cannot decide truth."
                ),
                recommended_review_role="c5isr manager",
                provenance_chain=tuple(event.provenance for event in selected),
                simulation_replay_available=True,
            )
        return None

    def _detect_operator_intel_mission_impact_conflict(
        self, events: tuple[Event, ...]
    ) -> ConflictPacket | None:
        operator_events = tuple(event for event in events if event.metadata.get("input_source") == "operator-mini")
        intel_events = tuple(event for event in events if event.metadata.get("input_source") == "jinx-intel")
        if not operator_events or not intel_events:
            return None

        operator_event = operator_events[-1]
        intel_event = intel_events[-1]
        confidence = self._confidence_engine.combine_for_conflict(
            (operator_event, intel_event),
            rationale="Synthetic operator and INTEL-derived inputs may affect the same mission assumptions.",
        )
        return ConflictPacket(
            conflict_type="operator_intel_mission_impact_conflict",
            detected_by_module="jinx-core",
            conflicting_items=(operator_event.id, intel_event.id),
            likely_impacts=(
                "Mission assumptions may need human review",
                "COP confidence may be affected by ISR-derived context",
                "Planner or analyst review may be useful before scenario assumptions are reused",
            ),
            potential_human_resolutions=(
                "Ask C5ISR and INTEL reviewers to compare the operator report and INTEL impact summary.",
                "Run a synthetic replay that includes both the operator event and INTEL-derived context.",
                "Annotate the mission assumption as pending human review.",
            ),
            confidence=confidence,
            explanation=(
                "Synthetic operator and INTEL-derived inputs both indicate possible mission impact. "
                "JINX-Core is flagging correlation for human review and does not determine truth."
            ),
            recommended_review_role="c5isr manager",
            provenance_chain=(operator_event.provenance, intel_event.provenance),
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

    @staticmethod
    def _status_claim(event: Event) -> str | None:
        explicit = event.metadata.get("status") or event.metadata.get("communications_status")
        if explicit in {"available", "unavailable"}:
            return explicit
        lowered = event.description.lower()
        if any(term in lowered for term in ("unavailable", "lost", "loss", "down", "not ready")):
            return "unavailable"
        if any(term in lowered for term in ("available", "restored", "ready", "green")):
            return "available"
        return None
