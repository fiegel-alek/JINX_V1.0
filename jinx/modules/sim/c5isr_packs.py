"""Reusable synthetic C5ISR scenario packs."""

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class C5ISRScenarioPack:
    name: str
    summary: str
    injects: tuple[dict[str, str], ...]
    expected_outputs: tuple[str, ...]
    id: str = field(default_factory=lambda: f"c5isr-scenario-{uuid4()}")

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("scenario pack name is required")
        if not self.summary:
            raise ValueError("scenario pack summary is required")
        if not self.injects:
            raise ValueError("scenario pack requires injects")
        if not self.expected_outputs:
            raise ValueError("scenario pack requires expected outputs")


def default_c5isr_scenario_packs() -> tuple[C5ISRScenarioPack, ...]:
    return (
        C5ISRScenarioPack(
            name="Conflicting Location Reports",
            summary="Two synthetic reports place the same operator in different grid areas.",
            injects=(
                {"type": "operator_report", "report_type": "position_update", "location": "grid-alpha"},
                {"type": "operator_report", "report_type": "position_update", "location": "grid-bravo"},
            ),
            expected_outputs=("cop_location_conflict", "human_review_path", "track_conflicting"),
        ),
        C5ISRScenarioPack(
            name="Comms Loss With ISR Weather Impact",
            summary="Operator reports communications loss while INTEL adds weather impact context.",
            injects=(
                {"type": "operator_report", "report_type": "communications_check", "summary": "comms lost"},
                {"type": "intel_summary", "summary": "synthetic weather and visibility impact"},
            ),
            expected_outputs=("communications_status_conflict", "weather mission impact", "network review"),
        ),
        C5ISRScenarioPack(
            name="Delayed Movement",
            summary="Synthetic status report indicates movement delay against mission timeline.",
            injects=(
                {"type": "operator_report", "report_type": "status_update", "summary": "movement delayed"},
            ),
            expected_outputs=("timeline mission impact", "c5isr review"),
        ),
        C5ISRScenarioPack(
            name="Route Hazard",
            summary="Synthetic hazard report affects route confidence.",
            injects=(
                {"type": "operator_report", "report_type": "hazard", "summary": "hazard near route"},
            ),
            expected_outputs=("route_confidence mission impact", "human review"),
        ),
        C5ISRScenarioPack(
            name="Medical Event",
            summary="Synthetic medical event requires C5ISR review and timeline awareness.",
            injects=(
                {"type": "operator_report", "report_type": "medical", "summary": "medical support review"},
            ),
            expected_outputs=("medical mission impact", "review queue"),
        ),
        C5ISRScenarioPack(
            name="Stale COP Track",
            summary="Synthetic track lifecycle scenario for stale-track styling and validation.",
            injects=(
                {"type": "operator_report", "report_type": "position_update", "location": "grid-alpha"},
            ),
            expected_outputs=("track lifecycle", "stale review"),
        ),
        C5ISRScenarioPack(
            name="Operator Report Plus INTEL Impact",
            summary="Operator report and INTEL summary combine into a mission-impact review packet.",
            injects=(
                {"type": "operator_report", "report_type": "hazard", "summary": "hazard near area"},
                {"type": "intel_summary", "summary": "synthetic communications and weather context"},
            ),
            expected_outputs=("operator_intel_mission_impact_conflict", "mission impact packet"),
        ),
        C5ISRScenarioPack(
            name="NET-Related Communications Issue",
            summary="Synthetic communications issue calls for JINX-NET review if licensed.",
            injects=(
                {"type": "operator_report", "report_type": "communications_check", "summary": "network down"},
            ),
            expected_outputs=("network manager review", "JINX-NET review recommended"),
        ),
    )
