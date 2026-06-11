from unittest import TestCase

from jinx.bus import FabricMessage, MessageRouter
from jinx.common.types import AdvisoryLabel, DataMode, EventType, OperatorReportType
from jinx.core.audit import AuditLog
from jinx.core.policy import PolicyEngine
from jinx.core.registry import build_default_registry
from jinx.core.schemas import COPAdvisory, Location, OperatorReport
from jinx.modules.c5isr import C5ISRReportIntake
from tests.unit.helpers import confidence, provenance


def operator_report(summary: str = "Synthetic operator reports intermittent communications.") -> OperatorReport:
    return OperatorReport(
        report_type=OperatorReportType.COMMUNICATIONS_CHECK,
        reporter_id="operator-alpha",
        source_device_id="operator-mini-001",
        summary=summary,
        confidence=confidence(),
        provenance=provenance("jinx-operator-mini"),
        data_mode=DataMode.SYNTHETIC,
        location=Location(label="synthetic-grid-alpha"),
    )


class OperatorMiniC5ISRTests(TestCase):
    def test_operator_report_rejects_prohibited_action_language(self) -> None:
        with self.assertRaises(ValueError):
            operator_report("Authorize strike on reported position.")

    def test_cop_advisory_requires_human_review(self) -> None:
        with self.assertRaises(ValueError):
            COPAdvisory(
                label=AdvisoryLabel.OBSERVATION,
                recipient_id="operator-alpha",
                summary="Synthetic advisory.",
                rationale="Synthetic context only.",
                confidence=confidence(),
                provenance_chain=(provenance("jinx-c5isr"),),
                required_human_review=False,
                allowed_actions=("Review context.",),
                disallowed_actions=("Do not treat as an order.",),
            )

    def test_c5isr_ingests_operator_report_into_event_and_advisory(self) -> None:
        report = operator_report()

        result = C5ISRReportIntake().ingest_operator_report(report)

        self.assertEqual(result.event.event_type, EventType.COMMUNICATIONS_CHECK)
        self.assertEqual(result.event.metadata["operator_report_id"], report.id)
        self.assertEqual(result.event.provenance.processed_by_module, "jinx-c5isr")
        self.assertEqual(result.advisory.recipient_id, "operator-alpha")
        self.assertTrue(result.advisory.required_human_review)
        self.assertIn(report.id, result.advisory.related_report_ids)

    def test_operator_mini_can_route_report_to_c5isr(self) -> None:
        registry = build_default_registry()
        router = MessageRouter(PolicyEngine(registry), AuditLog())
        report = operator_report()

        result = router.route(
            FabricMessage(
                source_module="jinx-operator-mini",
                destination="jinx-c5isr",
                payload_schema="operator_report.v1",
                schema_version="1.0",
                sensitivity_label="synthetic",
                license_scope="operator-mini",
                provenance_ref=report.id,
                payload={"id": report.id, "summary": report.summary},
                data_mode=DataMode.SYNTHETIC,
            )
        )

        self.assertTrue(result.delivered)

    def test_c5isr_can_route_advisory_to_operator_mini(self) -> None:
        registry = build_default_registry()
        router = MessageRouter(PolicyEngine(registry), AuditLog())
        report = operator_report()
        advisory = C5ISRReportIntake().ingest_operator_report(report).advisory

        result = router.route(
            FabricMessage(
                source_module="jinx-c5isr",
                destination="jinx-operator-mini",
                payload_schema="cop_advisory.v1",
                schema_version="1.0",
                sensitivity_label="synthetic",
                license_scope="c5isr",
                provenance_ref=advisory.id,
                payload={"id": advisory.id, "summary": advisory.summary},
                data_mode=DataMode.SYNTHETIC,
            )
        )

        self.assertTrue(result.delivered)
