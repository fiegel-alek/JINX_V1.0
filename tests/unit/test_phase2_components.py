from unittest import TestCase

from jinx.brain.knowledge.defaults import build_synthetic_doctrine_repository
from jinx.bus import BoundaryRoutingRule, FabricMessage, MessageRouter
from jinx.common.types import DataMode, EventType, HumanCommandType
from jinx.core.audit import AuditLog, AuditRecord
from jinx.common.types import AuditEventType
from jinx.core.memory import AuditRecordStore, ProvenanceRecordStore
from jinx.core.policy import PolicyEngine
from jinx.core.reasoning import CoreContextBuilder
from jinx.core.registry import build_default_registry
from jinx.core.schemas import EntityRef, Event, HumanCommandInput, Location
from jinx.modules.c5isr import COPManager
from jinx.modules.intel import IntelligenceFusionEngine, IntelligenceSummary
from jinx.modules.net import NetworkNode, NetworkStatus, NetworkValidator
from tests.unit.helpers import confidence, provenance


class Phase2ComponentTests(TestCase):
    def test_human_command_must_be_human_originated(self) -> None:
        with self.assertRaises(ValueError):
            HumanCommandInput(
                command_type=HumanCommandType.HUMAN_DIRECTION,
                issuing_user_id="commander-alpha",
                issuing_role="commander",
                text="Synthetic coordination instruction.",
                provenance=provenance("human-ui"),
                data_mode=DataMode.SYNTHETIC,
                target_module="jinx-c5isr",
                human_originated=False,
            )

    def test_human_command_rejects_core_generation(self) -> None:
        with self.assertRaises(ValueError):
            HumanCommandInput(
                command_type=HumanCommandType.HUMAN_DIRECTION,
                issuing_user_id="commander-alpha",
                issuing_role="commander",
                text="Synthetic coordination instruction.",
                provenance=provenance("human-ui"),
                data_mode=DataMode.SYNTHETIC,
                target_module="jinx-c5isr",
                generated_by_core=True,
            )

    def test_operator_mini_can_route_human_command_to_c5isr(self) -> None:
        registry = build_default_registry()
        router = MessageRouter(PolicyEngine(registry), AuditLog())

        result = router.route(
            FabricMessage(
                source_module="jinx-operator-mini",
                destination="jinx-c5isr",
                payload_schema="human_command.v1",
                schema_version="1.0",
                sensitivity_label="synthetic",
                license_scope="operator-mini",
                provenance_ref="human-cmd-001",
                payload={"id": "human-cmd-001", "text": "Synthetic human coordination input."},
                data_mode=DataMode.SYNTHETIC,
            )
        )

        self.assertTrue(result.delivered)

    def test_core_cannot_originate_human_command_route(self) -> None:
        registry = build_default_registry()
        router = MessageRouter(PolicyEngine(registry), AuditLog())

        result = router.route(
            FabricMessage(
                source_module="jinx-core",
                destination="jinx-c5isr",
                payload_schema="human_command.v1",
                schema_version="1.0",
                sensitivity_label="synthetic",
                license_scope="core",
                provenance_ref="human-cmd-001",
                payload={"id": "human-cmd-001", "text": "Core must not originate this."},
                data_mode=DataMode.SYNTHETIC,
            )
        )

        self.assertFalse(result.delivered)

    def test_cop_manager_builds_state_from_event(self) -> None:
        event = Event(
            event_type=EventType.POSITION_UPDATE,
            source="operator-mini-001",
            description="Synthetic operator position update.",
            confidence=confidence(),
            provenance=provenance("jinx-c5isr"),
            data_mode=DataMode.SYNTHETIC,
            location=Location(label="synthetic-grid-alpha"),
            metadata={"operator_report_id": "report-001", "reporter_id": "operator-alpha"},
        )
        manager = COPManager(name="synthetic-cop")

        manager.apply_event(event, entity=EntityRef("operator-alpha", "Operator Alpha", "operator"))
        state = manager.state()

        self.assertEqual(state.name, "synthetic-cop")
        self.assertEqual(len(state.tracks), 1)
        self.assertEqual(state.tracks[0].last_report_id, "report-001")

    def test_router_applies_boundary_redaction(self) -> None:
        registry = build_default_registry()
        audit_log = AuditLog()
        router = MessageRouter(
            PolicyEngine(registry),
            audit_log,
            boundary_rules=(
                BoundaryRoutingRule(
                    source_module="jinx-core",
                    destination_module="jinx-c5isr",
                    payload_schema="recommendation.v1",
                    allowed_fields=frozenset({"id", "text"}),
                    abstract_replacements={"intel_detail": "Restricted detail redacted."},
                ),
            ),
        )

        result = router.route(
            FabricMessage(
                source_module="jinx-core",
                destination="jinx-c5isr",
                payload_schema="recommendation.v1",
                schema_version="1.0",
                sensitivity_label="synthetic",
                license_scope="core",
                provenance_ref="rec-001",
                payload={
                    "id": "rec-001",
                    "text": "Human review recommended.",
                    "intel_detail": "Restricted synthetic context.",
                    "network_detail": "Restricted network context.",
                },
                data_mode=DataMode.SYNTHETIC,
            )
        )

        self.assertTrue(result.delivered)
        self.assertEqual(
            result.message.payload,
            {"id": "rec-001", "text": "Human review recommended.", "intel_detail": "Restricted detail redacted."},
        )
        self.assertIn(AuditEventType.BOUNDARY_REDACTION, [record.event_type for record in audit_log.records()])

    def test_core_context_builder_retrieves_brain_doctrine(self) -> None:
        event = Event(
            event_type=EventType.COMMUNICATIONS_CHECK,
            source="synthetic-feed",
            description="Synthetic communications check.",
            confidence=confidence(),
            provenance=provenance("jinx-sim"),
            data_mode=DataMode.SYNTHETIC,
        )

        context = CoreContextBuilder(build_synthetic_doctrine_repository()).build_for_events(
            (event,), doctrine_query="communications", doctrine_tags=frozenset({"review"})
        )

        self.assertGreaterEqual(len(context.doctrine_references), 1)

    def test_network_validator_flags_synthetic_issues(self) -> None:
        status = NetworkStatus(
            name="synthetic-mtdl",
            nodes=(NetworkNode("node-a", "Node A", "terminal"),),
            timeslot_conflicts=("node-a",),
            los_warnings=("node-a",),
            confidence=confidence(),
            provenance=provenance("jinx-net"),
            data_mode=DataMode.SYNTHETIC,
        )

        issues = NetworkValidator().validate(status)

        self.assertEqual([issue.issue_type for issue in issues], ["timeslot_conflict", "los_warning"])

    def test_intel_fusion_maps_authorized_summary_impacts(self) -> None:
        summary = IntelligenceSummary(
            source_category="synthetic_summary",
            summary="Synthetic weather and communications context may affect assumptions.",
            reliability=0.7,
            confidence=confidence(),
            provenance=provenance("jinx-intel"),
            data_mode=DataMode.SYNTHETIC,
            restrictions=("Synthetic summary only.",),
        )

        result = IntelligenceFusionEngine().fuse((summary,))

        self.assertEqual(
            {impact.impacted_area for impact in result.impacts},
            {"weather_constraints", "communications_assumptions"},
        )

    def test_memory_stores_hold_audit_and_provenance(self) -> None:
        audit_store = AuditRecordStore()
        provenance_store = ProvenanceRecordStore()
        audit = AuditRecord(
            event_type=AuditEventType.INPUT_RECEIVED,
            actor="jinx-test",
            summary="Synthetic input received.",
            metadata={"mode": "synthetic"},
        )
        prov = provenance("jinx-test")

        audit_store.save(audit)
        provenance_store.save(prov)

        self.assertEqual(audit_store.by_actor("jinx-test"), (audit,))
        self.assertEqual(provenance_store.by_module("jinx-test"), (prov,))
