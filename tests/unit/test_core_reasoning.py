from unittest import TestCase

from jinx.bus import MessageRouter
from jinx.common.types import AuditEventType, DataMode, EventType
from jinx.core.audit import AuditLog
from jinx.core.policy import PolicyEngine
from jinx.core.reasoning import CoreConflictDetector, CoreReasoningWorkflow
from jinx.core.registry import build_default_registry
from jinx.core.schemas import Event, Location
from jinx.modules.sim import SyntheticScenarioFactory
from tests.unit.helpers import confidence, provenance


class CoreReasoningTests(TestCase):
    def test_core_conflict_detector_finds_synthetic_communications_status_conflict(self) -> None:
        factory = SyntheticScenarioFactory()
        events = (factory.communications_available_event(), factory.communications_loss_event())

        conflicts = CoreConflictDetector().detect(events)

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].conflict_type, "communications_status_conflict")
        self.assertTrue(conflicts[0].simulation_replay_available)
        self.assertEqual(conflicts[0].detected_by_module, "jinx-core")
        self.assertIn("cannot decide which report is true", conflicts[0].explanation)

    def test_core_conflict_detector_finds_cop_location_conflict(self) -> None:
        events = (
            Event(
                event_type=EventType.POSITION_UPDATE,
                source="operator-mini-001",
                description="Synthetic position report at grid alpha.",
                confidence=confidence(),
                provenance=provenance("jinx-c5isr"),
                data_mode=DataMode.SYNTHETIC,
                location=Location("grid-alpha"),
                metadata={"reporter_id": "operator-alpha", "input_source": "operator-mini"},
            ),
            Event(
                event_type=EventType.POSITION_UPDATE,
                source="operator-mini-001",
                description="Synthetic position report at grid bravo.",
                confidence=confidence(),
                provenance=provenance("jinx-c5isr"),
                data_mode=DataMode.SYNTHETIC,
                location=Location("grid-bravo"),
                metadata={"reporter_id": "operator-alpha", "input_source": "operator-mini"},
            ),
        )

        conflicts = CoreConflictDetector().detect(events)

        self.assertEqual(conflicts[0].conflict_type, "cop_location_conflict")
        self.assertIn("Keep both locations visible", conflicts[0].potential_human_resolutions[2])

    def test_core_conflict_detector_flags_operator_intel_mission_impact_review(self) -> None:
        events = (
            Event(
                event_type=EventType.HAZARD,
                source="operator-mini-001",
                description="Synthetic operator hazard report.",
                confidence=confidence(),
                provenance=provenance("jinx-c5isr"),
                data_mode=DataMode.SYNTHETIC,
                metadata={"input_source": "operator-mini"},
            ),
            Event(
                event_type=EventType.WEATHER_IMPACT,
                source="jinx-intel",
                description="Synthetic INTEL weather impact.",
                confidence=confidence(),
                provenance=provenance("jinx-intel"),
                data_mode=DataMode.SYNTHETIC,
                metadata={"input_source": "jinx-intel", "impacted_area": "weather_constraints"},
            ),
        )

        conflicts = CoreConflictDetector().detect(events)

        self.assertEqual(conflicts[0].conflict_type, "operator_intel_mission_impact_conflict")
        self.assertIn("INTEL reviewers", conflicts[0].potential_human_resolutions[0])

    def test_core_conflict_detector_returns_empty_without_conflict(self) -> None:
        factory = SyntheticScenarioFactory()
        events = (factory.communications_available_event(),)

        self.assertEqual(CoreConflictDetector().detect(events), ())

    def test_core_workflow_routes_conflict_and_recommendation(self) -> None:
        factory = SyntheticScenarioFactory()
        registry = build_default_registry()
        audit_log = AuditLog()
        router = MessageRouter(PolicyEngine(registry), audit_log)
        workflow = CoreReasoningWorkflow(router)

        result = workflow.review_events(
            (factory.communications_available_event(), factory.communications_loss_event())
        )

        self.assertEqual(len(result.conflicts), 1)
        self.assertEqual(len(result.recommendations), 1)
        self.assertEqual(len(result.explanations), 2)
        self.assertIsNotNone(result.analysis_run)
        self.assertEqual(result.analysis_run.confidence_summary.band, "medium")
        self.assertTrue(result.analysis_run.human_review_required)
        self.assertTrue(result.recommendations[0].brain_references)
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
