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
            allowed_inputs=frozenset(
                {
                    "event.v1",
                    "conflict_packet.v1",
                    "recommendation.v1",
                    "human_command.v1",
                    "cop_state.v1",
                    "doctrine_reference.v1",
                    "intel_impact.v1",
                    "network_issue.v1",
                    "message_intake.v1",
                }
            ),
            allowed_outputs=frozenset(
                {
                    "policy_decision.v1",
                    "audit_record.v1",
                    "conflict_packet.v1",
                    "recommendation.v1",
                    "human_command_ack.v1",
                }
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
                    "human_command_carrier",
                    "memory_store",
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
            allowed_inputs=frozenset(
                {
                    "event.v1",
                    "conflict_packet.v1",
                    "recommendation.v1",
                    "operator_report.v1",
                    "cop_advisory.v1",
                    "human_command.v1",
                    "network_issue.v1",
                    "intel_impact.v1",
                    "isr_feed.v1",
                    "cop_state.v1",
                    "message_intake.v1",
                }
            ),
            allowed_outputs=frozenset(
                {
                    "event.v1",
                    "conflict_packet.v1",
                    "recommendation.v1",
                    "operator_report.v1",
                    "cop_advisory.v1",
                    "human_command.v1",
                    "network_issue.v1",
                    "intel_impact.v1",
                    "isr_feed.v1",
                    "cop_state.v1",
                    "message_intake.v1",
                }
            ),
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
            name="jinx-integrator",
            version="0.1.0",
            licensed=True,
            license_scope="integrator",
            allowed_inputs=frozenset(),
            allowed_outputs=frozenset({"message_intake.v1"}),
            required_permissions=frozenset({"mock_adapter:read", "audit:write"}),
            capabilities=frozenset(
                {
                    "bounded_message_ingest",
                    "message_family_parser_stub",
                    "optasklink_parser_stub",
                    "integration_node_map_design",
                    "jinx_architecture_design",
                    "schema_normalization",
                    "internal_fabric_routing",
                    "message_filtering",
                }
            ),
            dependencies=frozenset({"jinx-core", "jinx-bus"}),
            safety_classification=SafetyClassification.ADVISORY_REASONING,
            supports_simulation=True,
        ),
        ModuleManifest(
            name="jinx-c5isr",
            version="0.1.0",
            licensed=True,
            license_scope="c5isr",
            allowed_inputs=frozenset(
                {
                    "event.v1",
                    "conflict_packet.v1",
                    "recommendation.v1",
                    "operator_report.v1",
                    "human_command.v1",
                    "message_intake.v1",
                }
            ),
            allowed_outputs=frozenset({"event.v1", "conflict_packet.v1", "cop_advisory.v1", "cop_state.v1"}),
            required_permissions=frozenset({"mock_adapter:read", "audit:write"}),
            capabilities=frozenset(
                {
                    "cop_management_stub",
                    "potential_threat_detection_stub",
                    "isr_fusion_stub",
                    "warfighter_effects_review_stub",
                    "mission_parse_stub",
                    "event_parse_stub",
                    "operator_report_intake",
                    "cop_state_management",
                }
            ),
            dependencies=frozenset({"jinx-core", "jinx-brain", "jinx-bus"}),
            safety_classification=SafetyClassification.ADVISORY_REASONING,
            supports_simulation=True,
        ),
        ModuleManifest(
            name="jinx-operator-mini",
            version="0.1.0",
            licensed=True,
            license_scope="operator-mini",
            allowed_inputs=frozenset({"cop_advisory.v1", "recommendation.v1", "human_command_ack.v1"}),
            allowed_outputs=frozenset({"operator_report.v1", "human_command.v1"}),
            required_permissions=frozenset({"operator_report:write", "audit:write"}),
            capabilities=frozenset(
                {
                    "operator_report_submit",
                    "cop_advisory_receive",
                    "simulation_edge_client",
                    "disconnected_mock_mode",
                    "human_command_submit",
                }
            ),
            dependencies=frozenset({"jinx-c5isr"}),
            safety_classification=SafetyClassification.ADVISORY_REASONING,
            supports_simulation=True,
        ),
        ModuleManifest(
            name="jinx-net",
            version="0.1.0",
            licensed=True,
            license_scope="net",
            allowed_inputs=frozenset({"event.v1", "message_intake.v1"}),
            allowed_outputs=frozenset({"event.v1", "conflict_packet.v1", "network_issue.v1"}),
            required_permissions=frozenset({"mock_adapter:read", "audit:write"}),
            capabilities=frozenset(
                {
                    "mtdl_network_management_stub",
                    "issue_correction_stub",
                    "network_parse_stub",
                    "timing_check_stub",
                    "los_check_stub",
                    "synthetic_mtdl_validation",
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
            allowed_inputs=frozenset({"event.v1", "message_intake.v1"}),
            allowed_outputs=frozenset({"event.v1", "conflict_packet.v1", "intel_impact.v1", "isr_feed.v1"}),
            required_permissions=frozenset({"mock_adapter:read", "audit:write"}),
            capabilities=frozenset(
                {
                    "intelligence_fusion_stub",
                    "summary_ingest_stub",
                    "correlation_stub",
                    "impact_mapping_stub",
                    "authorized_summary_fusion",
                }
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
