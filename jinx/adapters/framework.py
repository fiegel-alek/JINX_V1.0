"""Controlled adapter framework."""

from dataclasses import dataclass

from jinx.common.types import DataMode, SafetyClassification


@dataclass(frozen=True, slots=True)
class AdapterManifest:
    name: str
    permission: str
    data_mode: DataMode
    safety_classification: SafetyClassification
    supports_simulation: bool = True
    explicitly_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("adapter name is required")
        if not self.permission:
            raise ValueError("adapter permission is required")
        if not self.supports_simulation:
            raise ValueError("adapters must support simulation mode")


class AdapterGate:
    def may_activate(self, manifest: AdapterManifest) -> bool:
        if manifest.data_mode == DataMode.LIVE_CONTROLLED_ADAPTER:
            return (
                manifest.explicitly_authorized
                and manifest.safety_classification == SafetyClassification.CONTROLLED_REAL_ADAPTER
            )
        return manifest.data_mode in {DataMode.SYNTHETIC, DataMode.MOCK, DataMode.OPEN, DataMode.AUTHORIZED}
