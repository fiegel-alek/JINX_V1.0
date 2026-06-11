from unittest import TestCase

from jinx.brain import BrainReasoningWorkflow, ConflictDetector
from jinx.bus import MessageRouter
from jinx.common.types import AuditEventType, EventType
from jinx.core.audit import AuditLog
from jinx.core.policy import PolicyEngine
from jinx.core.registry import build_default_registry
from jinx.modules.sim import SyntheticScenarioFactory


class BrainReasoningTests(TestCase):
    def test_conflict_detector_finds_synthetic_communications_status_conflict(self) -> None:
        factory = SyntheticScenarioFactory()
        events = (factory.communications_available_event(), factory.communications_loss_event())

        conflicts = ConflictDetector().detect(events)

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].conflict_type, "communications_status_conflict")
        self.assertTrue(conflicts[0].simulation_replay_available)
        self.assertIn("cannot decide which report is true", conflicts[0].explanation)

    def test_conflict_detector_returns_empty_without_conflict(self) -> None:
        factory = SyntheticScenarioFactory()
        events = (factory.communications_available_event(),)

        self.assertEqual(ConflictDetector().detect(events), ())

    def test_brain_workflow_routes_conflict_and_recommendation(self) -> None:
        factory = SyntheticScenarioFactory()
        registry = build_default_registry()
        audit_log = AuditLog()
        router = MessageRouter(PolicyEngine(registry), audit_log)
        workflow = BrainReasoningWorkflow(router)

        result = workflow.review_events(
            (factory.communications_available_event(), factory.communications_loss_event())
        )

        self.assertEqual(len(result.conflicts), 1)
        self.assertEqual(len(result.recommendations), 1)
        self.assertEqual(len(result.route_results), 2)
        self.assertTrue(all(route.delivered for route in result.route_results))
        self.assertEqual(
            [message.payload_schema for message in router.delivered_messages()],
            ["conflict_packet.v1", "recommendation.v1"],
        )
        self.assertEqual(
            [record.event_type for record in audit_log.records()],
            [
                AuditEventType.POLICY_DECISION,
                AuditEventType.MODULE_CALL,
                AuditEventType.POLICY_DECISION,
                AuditEventType.MODULE_CALL,
            ],
        )

    def test_simulation_factory_builds_available_baseline_event(self) -> None:
        event = SyntheticScenarioFactory().communications_available_event()

        self.assertEqual(event.event_type, EventType.COMMUNICATIONS_AVAILABLE)
        self.assertEqual(event.metadata["communications_status"], "available")
