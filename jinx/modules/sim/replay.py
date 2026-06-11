"""Deterministic scenario replay primitives."""

from dataclasses import dataclass

from jinx.modules.sim.scenarios import SimulationEvent, SimulationScenario


@dataclass(frozen=True, slots=True)
class ReplayFrame:
    offset_seconds: int
    event: SimulationEvent


@dataclass(frozen=True, slots=True)
class ReplayResult:
    scenario_id: str
    frames: tuple[ReplayFrame, ...]

    def __post_init__(self) -> None:
        if not self.frames:
            raise ValueError("replay result requires frames")


class ScenarioReplayer:
    def replay(self, scenario: SimulationScenario) -> ReplayResult:
        if not scenario.events:
            raise ValueError("cannot replay scenario without events")
        frames = tuple(
            ReplayFrame(offset_seconds=event.offset_seconds, event=event) for event in scenario.events
        )
        return ReplayResult(scenario_id=scenario.id, frames=frames)
