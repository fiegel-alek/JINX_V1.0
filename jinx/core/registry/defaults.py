"""Default module manifests for the JINX platform."""

from jinx.common.types import SafetyClassification
from jinx.core.registry.models import ModuleManifest, ModuleRegistry


def default_module_manifests() -> tuple[ModuleManifest, ...]:
    return (
        ModuleManifest(
            name="jinx-core",
            version="0.1.0",
            licensed=True,
            license_scope="core",
            allowed_inputs=frozenset({"event.v1", "conflict_packet.v1", "recommendation.v1"}),
            allowed_outputs=frozenset(
                {"policy_decision.v1", "audit_record.v1", "conflict_packet.v1", "recommendation.v1"}
            ),
            required_permissions=frozenset({"memory:write", "audit:write", "policy:evaluate"}),
            capabilities=frozenset(
                {
                    "ai_reasoning",
                    "analysis",
                    "task_execution",
                    "conflict_detection",
                    "confidence",
                    "explanation",
                    "registry",
                    "policy",
                    "audit",
                    "provenance",
                }
            ),
            dependencies=frozenset({"jinx-brain"}),
            safety_classification=SafetyClassification.CORE_PLATFORM,
            supports_simulation=True,
        ),
        ModuleManifest(
            name="jinx-bus",
            version="0.1.0",
            licensed=True,
            license_scope="fabric",
            allowed_inputs=frozenset({"event.v1", "conflict_packet.v1", "recommendation.v1"}),
            allowed_outputs=frozenset({"event.v1", "conflict_packet.v1", "recommendation.v1"}),
            required_permissions=frozenset({"policy:evaluate", "audit:write"}),
            capabilities=frozenset(
                {"policy_route", "dead_letter", "audit_hook", "tactical_radio_integration_stub"}
            ),
            dependencies=frozenset({"jinx-core"}),
            safety_classification=SafetyClassification.CORE_PLATFORM,
            supports_simulation=True,
        ),
        ModuleManifest(
            name="jinx-brain",
            version="0.1.0",
            licensed=True,
            license_scope="brain",
            allowed_inputs=frozenset({"doctrine_query.v1", "mission_context.v1"}),
            allowed_outputs=frozenset({"doctrine_reference.v1", "sop_reference.v1", "tacsop_reference.v1"}),
            required_permissions=frozenset({"doctrine:read", "audit:write"}),
            capabilities=frozenset({"doctrine_reference", "tacsop_reference", "sop_reference"}),
            dependencies=frozenset(),
            safety_classification=SafetyClassification.ADVISORY_REASONING,
            supports_simulation=True,
        ),
        ModuleManifest(
            name="jinx-c5isr",
            version="0.1.0",
            licensed=True,
            license_scope="c5isr",
            allowed_inputs=frozenset({"event.v1", "conflict_packet.v1", "recommendation.v1"}),
            allowed_outputs=frozenset({"event.v1", "conflict_packet.v1"}),
            required_permissions=frozenset({"mock_adapter:read", "audit:write"}),
            capabilities=frozenset(
                {
                    "cop_management_stub",
                    "potential_threat_detection_stub",
                    "isr_fusion_stub",
                    "warfighter_effects_review_stub",
                    "mission_parse_stub",
                    "event_parse_stub",
                }
            ),
            dependencies=frozenset({"jinx-core", "jinx-brain", "jinx-bus"}),
            safety_classification=SafetyClassification.ADVISORY_REASONING,
            supports_simulation=True,
        ),
        ModuleManifest(
            name="jinx-net",
            version="0.1.0",
            licensed=True,
            license_scope="net",
            allowed_inputs=frozenset({"event.v1"}),
            allowed_outputs=frozenset({"event.v1", "conflict_packet.v1"}),
            required_permissions=frozenset({"mock_adapter:read", "audit:write"}),
            capabilities=frozenset(
                {
                    "mtdl_network_management_stub",
                    "issue_correction_stub",
                    "network_parse_stub",
                    "timing_check_stub",
                    "los_check_stub",
                }
            ),
            dependencies=frozenset({"jinx-core", "jinx-brain", "jinx-bus"}),
            safety_classification=SafetyClassification.ADVISORY_REASONING,
            supports_simulation=True,
        ),
        ModuleManifest(
            name="jinx-intel",
            version="0.1.0",
            licensed=True,
            license_scope="intel",
            allowed_inputs=frozenset({"event.v1"}),
            allowed_outputs=frozenset({"event.v1", "conflict_packet.v1"}),
            required_permissions=frozenset({"mock_adapter:read", "audit:write"}),
            capabilities=frozenset(
                {"intelligence_fusion_stub", "summary_ingest_stub", "correlation_stub", "impact_mapping_stub"}
            ),
            dependencies=frozenset({"jinx-core", "jinx-brain", "jinx-bus"}),
            safety_classification=SafetyClassification.ADVISORY_REASONING,
            supports_simulation=True,
        ),
        ModuleManifest(
            name="jinx-sim",
            version="0.1.0",
            licensed=True,
            license_scope="simulation",
            allowed_inputs=frozenset({"scenario.v1"}),
            allowed_outputs=frozenset({"event.v1"}),
            required_permissions=frozenset({"audit:write"}),
            capabilities=frozenset({"scenario_generate", "timeline_replay", "synthetic_feed"}),
            dependencies=frozenset({"jinx-core", "jinx-bus"}),
            safety_classification=SafetyClassification.SIMULATION,
            supports_simulation=True,
        ),
    )


def build_default_registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    for manifest in default_module_manifests():
        registry.register(manifest)
    return registry
