"""C5ISR event classification for synthetic operator and INTEL inputs."""

from dataclasses import dataclass

from jinx.common.types import EventType, OperatorReportType
from jinx.modules.intel import IntelligenceImpact


@dataclass(frozen=True, slots=True)
class C5ISREventClassification:
    event_type: EventType
    rationale: str
    mission_impact_tags: tuple[str, ...]
    requires_human_review: bool = True


class C5ISREventClassifier:
    def classify_operator_report(
        self, report_type: OperatorReportType, summary: str
    ) -> C5ISREventClassification:
        lowered = summary.lower()
        if report_type == OperatorReportType.COMMUNICATIONS_CHECK:
            if any(term in lowered for term in ("loss", "lost", "outage", "down", "unavailable")):
                return C5ISREventClassification(
                    event_type=EventType.COMMUNICATIONS_LOSS,
                    rationale="Operator report indicates communications may be unavailable.",
                    mission_impact_tags=("communications", "cop_confidence"),
                )
            if any(term in lowered for term in ("available", "restored", "good", "green")):
                return C5ISREventClassification(
                    event_type=EventType.COMMUNICATIONS_AVAILABLE,
                    rationale="Operator report indicates communications may be available.",
                    mission_impact_tags=("communications", "cop_confidence"),
                )
            return C5ISREventClassification(
                event_type=EventType.COMMUNICATIONS_CHECK,
                rationale="Operator report requires communications review.",
                mission_impact_tags=("communications",),
            )
        if report_type == OperatorReportType.POSITION_UPDATE:
            return C5ISREventClassification(
                event_type=EventType.POSITION_UPDATE,
                rationale="Operator report updates a COP track location.",
                mission_impact_tags=("cop_track", "location"),
            )
        if report_type == OperatorReportType.STATUS_UPDATE:
            if any(term in lowered for term in ("delay", "delayed", "late", "stalled")):
                return C5ISREventClassification(
                    event_type=EventType.MOVEMENT_DELAY,
                    rationale="Operator status report indicates movement timing may be affected.",
                    mission_impact_tags=("timeline", "movement"),
                )
            return C5ISREventClassification(
                event_type=EventType.STATUS_UPDATE,
                rationale="Operator status report updates C5ISR context.",
                mission_impact_tags=("unit_status",),
            )
        if report_type == OperatorReportType.LOGISTICS:
            return C5ISREventClassification(
                event_type=EventType.LOGISTICS_ISSUE,
                rationale="Operator report indicates a logistics impact requiring review.",
                mission_impact_tags=("logistics", "mission_support"),
            )
        if report_type == OperatorReportType.MEDICAL:
            return C5ISREventClassification(
                event_type=EventType.MEDICAL_EVENT,
                rationale="Operator report indicates a medical event requiring human review.",
                mission_impact_tags=("medical", "personnel_status"),
            )
        if report_type == OperatorReportType.HAZARD:
            return C5ISREventClassification(
                event_type=EventType.HAZARD,
                rationale="Operator report indicates a hazard requiring C5ISR review.",
                mission_impact_tags=("hazard", "route", "safety"),
            )
        return C5ISREventClassification(
            event_type=EventType.UNKNOWN_REQUIRES_REVIEW,
            rationale="Operator report could not be classified confidently.",
            mission_impact_tags=("human_review",),
        )

    def classify_intel_impact(self, impact: IntelligenceImpact) -> C5ISREventClassification:
        impacted_area = impact.impacted_area.lower()
        if "weather" in impacted_area:
            return C5ISREventClassification(
                event_type=EventType.WEATHER_IMPACT,
                rationale="INTEL impact maps to weather constraints.",
                mission_impact_tags=("weather", "movement", "communications"),
            )
        if "communications" in impacted_area:
            return C5ISREventClassification(
                event_type=EventType.COMMUNICATIONS_CHECK,
                rationale="INTEL impact maps to communications assumptions.",
                mission_impact_tags=("communications", "network_review"),
            )
        return C5ISREventClassification(
            event_type=EventType.MISSION_IMPACT,
            rationale="INTEL impact may affect mission assumptions and requires review.",
            mission_impact_tags=("mission_assumptions", "human_review"),
        )
