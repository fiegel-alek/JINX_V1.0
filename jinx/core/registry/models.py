"""Module manifest and registry primitives."""

from dataclasses import dataclass, field

from jinx.common.types.enums import SafetyClassification


@dataclass(frozen=True, slots=True)
class ModuleManifest:
    name: str
    version: str
    licensed: bool
    license_scope: str
    allowed_inputs: frozenset[str]
    allowed_outputs: frozenset[str]
    required_permissions: frozenset[str]
    capabilities: frozenset[str]
    dependencies: frozenset[str]
    safety_classification: SafetyClassification
    supports_simulation: bool

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("module name is required")
        if not self.version:
            raise ValueError("module version is required")
        if not self.license_scope:
            raise ValueError("module license_scope is required")
        if not self.supports_simulation:
            raise ValueError("JINX modules must support simulation mode")


@dataclass(slots=True)
class ModuleRegistry:
    _modules: dict[str, ModuleManifest] = field(default_factory=dict)

    def register(self, manifest: ModuleManifest) -> None:
        if manifest.name in self._modules:
            raise ValueError(f"module already registered: {manifest.name}")
        self._modules[manifest.name] = manifest

    def get(self, name: str) -> ModuleManifest:
        try:
            return self._modules[name]
        except KeyError as exc:
            raise KeyError(f"module not registered: {name}") from exc

    def licensed_modules(self) -> tuple[ModuleManifest, ...]:
        return tuple(module for module in self._modules.values() if module.licensed)
