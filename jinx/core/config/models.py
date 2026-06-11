"""Runtime configuration for JINX."""

from dataclasses import dataclass
from pathlib import Path

from jinx.common.types import DataMode


@dataclass(frozen=True, slots=True)
class JINXConfig:
    data_mode: DataMode
    storage_root: Path
    simulation_first: bool = True
    real_adapters_enabled: bool = False

    def __post_init__(self) -> None:
        if not self.storage_root:
            raise ValueError("storage_root is required")
        if self.real_adapters_enabled and self.simulation_first:
            raise ValueError("real adapters cannot be enabled while simulation_first is true")
