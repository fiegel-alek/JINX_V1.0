"""Conservative policy engine for module interactions."""

from dataclasses import dataclass
from datetime import UTC, datetime

from jinx.common.types.enums import DataMode, SafetyClassification
from jinx.core.registry.models import ModuleManifest, ModuleRegistry


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    reason: str
    timestamp: datetime


class PolicyEngine:
    def __init__(self, registry: ModuleRegistry) -> None:
        self._registry = registry

    def may_route(
        self,
        source_module: str,
        destination_module: str,
        payload_schema: str,
        data_mode: DataMode,
    ) -> PolicyDecision:
        source = self._registry.get(source_module)
        destination = self._registry.get(destination_module)

        if not source.licensed or not destination.licensed:
            return self._deny("source and destination modules must both be licensed")
        if payload_schema not in source.allowed_outputs:
            return self._deny(f"{source.name} may not emit schema {payload_schema}")
        if payload_schema not in destination.allowed_inputs:
            return self._deny(f"{destination.name} may not receive schema {payload_schema}")
        if data_mode == DataMode.LIVE_CONTROLLED_ADAPTER:
            return self._deny("live adapter data requires explicit adapter authorization")
        return self._allow("route allowed by license, schema, and data-mode policy")

    def may_use_adapter(self, module_name: str, adapter_permission: str, data_mode: DataMode) -> PolicyDecision:
        module = self._registry.get(module_name)
        if not module.licensed:
            return self._deny("module is not licensed")
        if adapter_permission not in module.required_permissions:
            return self._deny(f"module lacks adapter permission {adapter_permission}")
        if data_mode == DataMode.LIVE_CONTROLLED_ADAPTER and module.safety_classification not in {
            SafetyClassification.CONTROLLED_REAL_ADAPTER,
            SafetyClassification.CORE_PLATFORM,
        }:
            return self._deny("live adapter use is restricted to controlled adapter paths")
        return self._allow("adapter use allowed")

    @staticmethod
    def _allow(reason: str) -> PolicyDecision:
        return PolicyDecision(True, reason, datetime.now(UTC))

    @staticmethod
    def _deny(reason: str) -> PolicyDecision:
        return PolicyDecision(False, reason, datetime.now(UTC))
