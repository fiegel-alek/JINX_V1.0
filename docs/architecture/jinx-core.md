# JINX-Core

JINX-Core is the main system where AI processing, analysis, policy enforcement, provenance, audit, and advisory task execution live.

Core owns the platform rules and performs bounded reasoning across approved inputs. It may analyze, explain, recommend, validate, simulate, and route human-review outputs. It must not command, target, collect, control weapons, or override human authority.

## Phase 1 Behavior

- Consumes synthetic events.
- Detects bounded communications status conflicts.
- Produces confidence-rated `ConflictPacket` objects.
- Produces human-review `Recommendation` objects.
- Routes advisory outputs through policy and audit paths.

## Relationship To BRAIN

BRAIN feeds Core with doctrine, TACSOP, SOP, and mission-knowledge references. Core performs the active reasoning and advisory output generation.
