# JINX-SIM

JINX-SIM is the synthetic environment for safe development, replay, and validation. It produces clearly labeled synthetic scenarios and events before any live adapter exists.

## Phase 1 Behavior

- Simulation scenarios must be labeled synthetic.
- Simulation events must declare synthetic status in their payloads.
- Scenario timelines must be deterministic and sorted by offset.
- The first factory creates a communications conflict shadow-run scenario for testing policy, bus, and advisory behavior.

## Future Work

- Scenario import and export.
- Timeline replay clock.
- Randomized stress generation with deterministic seeds.
- Expected-vs-actual comparison reports.
- Human-in-the-loop simulation controls.
