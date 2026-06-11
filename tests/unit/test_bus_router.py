from unittest import TestCase

from jinx.bus import BoundaryRoutingRule, FabricMessage, MessageRouter
from jinx.common.types import AuditEventType, DataMode, SafetyClassification
from jinx.core.audit import AuditLog
from jinx.core.policy import PolicyEngine
from jinx.core.registry import ModuleManifest, ModuleRegistry


def manifest(
    name: str,
    licensed: bool = True,
    allowed_inputs: frozenset[str] = frozenset({"event.v1"}),
    allowed_outputs: frozenset[str] = frozenset({"event.v1"}),
) -> ModuleManifest:
    return ModuleManifest(
        name=name,
        version="0.1.0",
        licensed=licensed,
        license_scope=name,
        allowed_inputs=allowed_inputs,
        allowed_outputs=allowed_outputs,
        required_permissions=frozenset({"mock_adapter:read"}),
        capabilities=frozenset({"simulation"}),
        dependencies=frozenset(),
        safety_classification=SafetyClassification.ADVISORY_REASONING,
        supports_simulation=True,
    )


def message(destination: str = "jinx-core") -> FabricMessage:
    return FabricMessage(
        source_module="jinx-sim",
        destination=destination,
        payload_schema="event.v1",
        schema_version="1.0",
        sensitivity_label="synthetic",
        license_scope="simulation",
        provenance_ref="prov-001",
        payload={"synthetic": True, "summary": "Synthetic event."},
        data_mode=DataMode.SYNTHETIC,
    )


class BusRouterTests(TestCase):
    def test_router_delivers_policy_allowed_message_and_audits(self) -> None:
        registry = ModuleRegistry()
        registry.register(manifest("jinx-sim"))
        registry.register(manifest("jinx-core"))
        audit_log = AuditLog()

        result = MessageRouter(PolicyEngine(registry), audit_log).route(message())

        self.assertTrue(result.delivered)
        self.assertEqual(result.status, "delivered")
        self.assertEqual(len(audit_log.records()), 2)
        self.assertEqual(audit_log.records()[0].event_type, AuditEventType.POLICY_DECISION)
        self.assertEqual(audit_log.records()[1].event_type, AuditEventType.MODULE_CALL)
        self.assertEqual(result.message.topic, "sim.event")

    def test_router_dead_letters_policy_denied_message(self) -> None:
        registry = ModuleRegistry()
        registry.register(manifest("jinx-sim"))
        registry.register(manifest("jinx-net", licensed=False))
        router = MessageRouter(PolicyEngine(registry), AuditLog())

        result = router.route(message(destination="jinx-net"))

        self.assertFalse(result.delivered)
        self.assertEqual(result.status, "denied")
        self.assertEqual(len(router.dead_letters()), 1)
        self.assertEqual(len(router.delivered_messages()), 0)
        self.assertEqual(router.route_records()[0].to_document()["status"], "denied")

    def test_router_records_boundary_redactions(self) -> None:
        registry = ModuleRegistry()
        registry.register(manifest("jinx-sim"))
        registry.register(manifest("jinx-core"))
        router = MessageRouter(
            PolicyEngine(registry),
            AuditLog(),
            boundary_rules=(
                BoundaryRoutingRule(
                    source_module="jinx-sim",
                    destination_module="jinx-core",
                    payload_schema="event.v1",
                    allowed_fields=frozenset({"summary"}),
                    abstract_replacements={"secret": "redacted by boundary"},
                ),
            ),
        )

        result = router.route(
            FabricMessage(
                source_module="jinx-sim",
                destination="jinx-core",
                payload_schema="event.v1",
                schema_version="1.0",
                sensitivity_label="synthetic",
                license_scope="simulation",
                provenance_ref="prov-002",
                payload={"summary": "Synthetic event.", "secret": "hidden domain detail"},
                data_mode=DataMode.SYNTHETIC,
                topic="sim.boundary-test",
            )
        )

        self.assertTrue(result.delivered)
        self.assertEqual(result.status, "redacted")
        self.assertEqual(result.redacted_fields, ("secret",))
        self.assertEqual(result.message.payload["secret"], "redacted by boundary")
        document = router.route_records()[0].to_document()
        self.assertEqual(document["topic"], "sim.boundary-test")
        self.assertEqual(document["redacted_fields"], ["secret"])
