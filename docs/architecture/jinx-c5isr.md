# JINX-C5ISR

JINX-C5ISR is for COP management, potential threat detection, ISR fusion, and awareness of anything that could affect troops, warfighters, operators, or command elements.

It remains advisory and human-in-the-loop. It may surface observations, warnings, confidence-limited assessments, and human-review prompts. It must not issue orders, prioritize lethal action, or override command judgment.

## Operator Mini Relationship

JINX-C5ISR may receive reports from JINX-Operator Mini clients. These reports are treated as human-originated field observations until reviewed, correlated, and assessed.

C5ISR may return:

- COP advisories
- confidence-limited observations
- human-review prompts
- context updates
- safety or communications warnings

C5ISR must not return operational orders, autonomous tasking, targeting decisions, or weapons-control instructions.

## Phase 2 Behavior

- Converts operator reports into normalized events.
- Builds COP tracks from event locations and provenance.
- Produces COP state snapshots for Core review and audit.
