"""Mission context and impact analysis for JINX-C5ISR."""

from jinx.common.types import EventType
from jinx.core.schemas import Event, MissionContext, MissionImpactPacket


class MissionImpactAnalyzer:
    def analyze(
        self,
        mission: MissionContext,
        events: tuple[Event, ...],
    ) -> tuple[MissionImpactPacket, ...]:
        impacts: list[MissionImpactPacket] = []
        for event in events:
            impact_area = self._impact_area(event)
            if impact_area is None:
                continue
            affected_routes = self._matching_values(event, mission.routes)
            affected_areas = self._matching_values(event, mission.named_areas)
            affected_tasks = self._affected_tasks(mission, affected_routes, affected_areas, impact_area)
            impacts.append(
                MissionImpactPacket(
                    impacted_area=impact_area,
                    summary=self._summary_for_event(event, impact_area),
                    source_event_ids=(event.id,),
                    affected_tasks=affected_tasks,
                    affected_routes=affected_routes,
                    affected_named_areas=affected_areas,
                    confidence=event.confidence,
                    rationale=(
                        "C5ISR mapped the event category and known mission context to possible affected "
                        "tasks, routes, named areas, or assumptions. This is advisory and requires review."
                    ),
                    recommended_review_role=self._review_role(impact_area),
                    required_human_review=True,
                    provenance_chain=(event.provenance, mission.provenance),
                )
            )
        return tuple(impacts)

    @staticmethod
    def _impact_area(event: Event) -> str | None:
        mapping = {
            EventType.COMMUNICATIONS_AVAILABLE: "communications",
            EventType.COMMUNICATIONS_CHECK: "communications",
            EventType.COMMUNICATIONS_LOSS: "communications",
            EventType.HAZARD: "route_confidence",
            EventType.ISR_UPDATE: "isr_assumptions",
            EventType.LOGISTICS_ISSUE: "logistics",
            EventType.MEDICAL_EVENT: "medical",
            EventType.MISSION_IMPACT: "mission_assumptions",
            EventType.MOVEMENT_DELAY: "timeline",
            EventType.POSITION_UPDATE: "cop_confidence",
            EventType.ROUTE_ISSUE: "route_confidence",
            EventType.STATUS_UPDATE: "unit_status",
            EventType.WEATHER_IMPACT: "weather",
        }
        return mapping.get(event.event_type)

    @staticmethod
    def _matching_values(event: Event, candidates: tuple[str, ...]) -> tuple[str, ...]:
        haystack = " ".join(
            (
                event.description,
                event.location.label if event.location else "",
                event.metadata.get("mission_impact_tags", ""),
                event.metadata.get("impacted_area", ""),
            )
        ).lower()
        return tuple(candidate for candidate in candidates if candidate.lower() in haystack)

    @staticmethod
    def _affected_tasks(
        mission: MissionContext,
        affected_routes: tuple[str, ...],
        affected_areas: tuple[str, ...],
        impact_area: str,
    ) -> tuple[str, ...]:
        affected: list[str] = []
        for task in mission.tasks:
            route_match = task.route in affected_routes if task.route else False
            area_match = task.named_area in affected_areas if task.named_area else False
            constraint_match = any(impact_area in constraint.lower() for constraint in task.constraints)
            if route_match or area_match or constraint_match:
                affected.append(task.task_id)
        if not affected and mission.tasks:
            affected.append(mission.tasks[0].task_id)
        return tuple(affected)

    @staticmethod
    def _summary_for_event(event: Event, impact_area: str) -> str:
        return f"{event.event_type.value} may affect {impact_area}: {event.description}"

    @staticmethod
    def _review_role(impact_area: str) -> str:
        if impact_area == "communications":
            return "network manager"
        if impact_area in {"isr_assumptions", "weather"}:
            return "intel analyst"
        return "c5isr manager"
