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
                "jinx-net",
                "jinx-intel",
                "jinx-sim",
            },
        )

    def test_default_registry_registers_all_modules(self) -> None:
        registry = build_default_registry()

        self.assertEqual(len(registry.licensed_modules()), 7)
        self.assertEqual(registry.get("jinx-sim").license_scope, "simulation")
