# JINX-BRAIN

JINX-BRAIN is the bounded reasoning subsystem. It receives scoped context through Core-approved paths and emits explainable advisory outputs only.

## Phase 1 Behavior

- Detects a synthetic communications status conflict when one synthetic event says communications are available and another says they are unavailable.
- Produces a `ConflictPacket` with confidence, explanation, likely impacts, review role, and provenance.
- Produces a human-review `Recommendation` from the conflict packet.
- Routes conflict and recommendation messages through JINX-BUS so policy and audit behavior are exercised.

## Boundary

The current detector does not decide which source is true. It labels the conflict, preserves uncertainty, recommends review, and supports simulation replay.

## Future Work

- Bounded context builder.
- Multi-conflict ranking.
- Clarification question generation.
- License-aware explanation redaction.
- Conservative feedback and learning gates.
