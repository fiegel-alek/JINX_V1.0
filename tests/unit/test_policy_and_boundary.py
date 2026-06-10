from unittest import TestCase

from jinx.boundary.entitlement import EntitlementBoundary
from jinx.common.types import DataMode, SafetyClassification
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


class PolicyAndBoundaryTests(TestCase):
    def test_policy_denies_unlicensed_destination(self) -> None:
        registry = ModuleRegistry()
        registry.register(manifest("jinx-c5isr"))
        registry.register(manifest("jinx-net", licensed=False))

        decision = PolicyEngine(registry).may_route(
            source_module="jinx-c5isr",
            destination_module="jinx-net",
            payload_schema="event.v1",
            data_mode=DataMode.SYNTHETIC,
        )

        self.assertFalse(decision.allowed)

    def test_policy_denies_live_adapter_data_by_default(self) -> None:
        registry = ModuleRegistry()
        registry.register(manifest("jinx-c5isr"))
        registry.register(manifest("jinx-core"))

        decision = PolicyEngine(registry).may_route(
            source_module="jinx-c5isr",
            destination_module="jinx-core",
            payload_schema="event.v1",
            data_mode=DataMode.LIVE_CONTROLLED_ADAPTER,
        )

        self.assertFalse(decision.allowed)

    def test_boundary_redacts_unlicensed_domain_fields(self) -> None:
        payload = {
            "summary": "Unit delayed.",
            "network_cause": "TDMA timeslot conflict.",
            "intel_cause": "Restricted intelligence-derived context.",
        }

        result = EntitlementBoundary().redact(
            payload=payload,
            allowed_fields=frozenset({"summary"}),
            abstract_replacements={
                "network_cause": "Communications issue detected. Network-domain review recommended."
            },
        )

        self.assertEqual(
            result.payload,
            {
                "summary": "Unit delayed.",
                "network_cause": "Communications issue detected. Network-domain review recommended.",
            },
        )
        self.assertEqual(set(result.redacted_fields), {"network_cause", "intel_cause"})
