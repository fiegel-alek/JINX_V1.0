# JINX-NET

JINX-NET is for Multi-Tactical Data Link network management, validation, simulation, and issue correction.

Initial development remains synthetic and mock-only. JINX-NET should help reason about MTDL network status, timing issues, configuration inconsistencies, interoperability concerns, and corrective review paths.

JINX-NET must not directly control live radios or modify live network configurations by default.

## Phase 2 Behavior

- Represents synthetic MTDL network nodes and status.
- Flags synthetic timeslot conflicts for human network-manager review.
- Flags synthetic line-of-sight warnings for human network-manager review.
