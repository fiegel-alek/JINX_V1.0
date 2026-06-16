from unittest import TestCase

from jinx.core.registry import build_default_registry, default_module_manifests


class DefaultRegistryTests(TestCase):
    def test_default_manifests_include_major_modules(self) -> None:
        names = {manifest.name for manifest in default_module_manifests()}

        self.assertEqual(
            names,
            {
                "jinx-core",
                "jinx-bus",
                "jinx-brain",
                "jinx-c5isr",
                "jinx-operator-mini",
                "jinx-net",
                "jinx-intel",
                "jinx-integrator",
                "jinx-sim",
            },
        )

    def test_default_registry_registers_all_modules(self) -> None:
        registry = build_default_registry()

        self.assertEqual(len(registry.licensed_modules()), 9)
        self.assertEqual(registry.get("jinx-sim").license_scope, "simulation")

    def test_default_registry_reflects_core_and_brain_roles(self) -> None:
        registry = build_default_registry()

        self.assertIn("ai_reasoning", registry.get("jinx-core").capabilities)
        self.assertIn("doctrine_reference", registry.get("jinx-brain").capabilities)
        self.assertIn("jinx-brain", registry.get("jinx-core").dependencies)
        self.assertIn("tactical_radio_integration_stub", registry.get("jinx-bus").capabilities)
        self.assertIn("operator_report_submit", registry.get("jinx-operator-mini").capabilities)
        self.assertIn("bounded_message_ingest", registry.get("jinx-integrator").capabilities)
        self.assertIn("jinx_architecture_design", registry.get("jinx-integrator").capabilities)
