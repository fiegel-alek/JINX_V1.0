from unittest import TestCase

from jinx.common.types import AdvisoryLabel, DataMode, EventType, OperatorReportType
from jinx.core.schemas import ConflictPacket, Event, Location, Recommendation
from jinx.core.schemas import COPAdvisory, OperatorReport
from tests.unit.helpers import confidence, provenance


class DomainSchemaTests(TestCase):
    def test_location_rejects_invalid_coordinates(self) -> None:
        with self.assertRaises(ValueError):
            Location(label="invalid", latitude=91.0)

    def test_synthetic_event_requires_simulation_flag(self) -> None:
        with self.assertRaises(ValueError):
            Event(
                event_type=EventType.CONFLICTING_REPORT,
                source="synthetic-feed",
                description="Synthetic report.",
                confidence=confidence(),
                provenance=provenance(),
                data_mode=DataMode.SYNTHETIC,
                simulation_flag=False,
            )

    def test_conflict_packet_requires_two_items(self) -> None:
        with self.assertRaises(ValueError):
            ConflictPacket(
                conflict_type="communications_status_conflict",
                detected_by_module="jinx-brain",
                conflicting_items=("report-a",),
                likely_impacts=("human review needed",),
                confidence=confidence(),
                explanation="Only one item is not enough to establish a conflict packet.",
                recommended_review_role="analyst",
                provenance_chain=(provenance("jinx-brain"),),
            )

    def test_recommendation_requires_human_review(self) -> None:
        with self.assertRaises(ValueError):
            Recommendation(
                recommendation_type="review_path",
                text="Review the synthetic conflict packet.",
                rationale="The report conflicts with baseline expectations.",
                assumptions=("Synthetic input only.",),
                risks=("Incomplete context.",),
                tradeoffs=("May require replay time.",),
                confidence=confidence(),
                required_human_review=False,
                allowed_actions=("Run synthetic replay.",),
                disallowed_actions=("Do not modify live systems.",),
                provenance_chain=(provenance("jinx-brain"),),
            )

    def test_operator_report_requires_human_origin(self) -> None:
        with self.assertRaises(ValueError):
            OperatorReport(
                report_type=OperatorReportType.OBSERVATION,
                reporter_id="operator-alpha",
                source_device_id="operator-mini-001",
                summary="Synthetic observation.",
                confidence=confidence(),
                provenance=provenance("jinx-operator-mini"),
                data_mode=DataMode.SYNTHETIC,
                human_originated=False,
            )

    def test_cop_advisory_rejects_prohibited_action_language(self) -> None:
        with self.assertRaises(ValueError):
            COPAdvisory(
                label=AdvisoryLabel.RECOMMENDATION,
                recipient_id="operator-alpha",
                summary="Engage target from advisory.",
                rationale="Unsafe advisory language should be rejected.",
                confidence=confidence(),
                provenance_chain=(provenance("jinx-c5isr"),),
                required_human_review=True,
                allowed_actions=("Request human review.",),
                disallowed_actions=("Do not treat as an order.",),
            )
