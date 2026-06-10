# Safety Guardrails

JINX exists to reduce cognitive overload and improve cross-system coherence while preserving human authority.

## Required Behavior

- Outputs are observations, assessments, warnings, recommendations, simulation results, confidence-limited inferences, or human-review prompts.
- Important outputs include confidence, explanation, and provenance.
- All simulation data is clearly marked synthetic.
- All real-world adapter access is explicit, permissioned, and audited.
- Boundary redactions are themselves auditable events.

## Prohibited Behavior

JINX must not:

- issue operational orders
- control weapons or physical effects
- perform autonomous targeting
- retask intelligence collection assets
- hide uncertainty
- bypass provenance
- leak licensed or compartmented information across module boundaries
- train shared behavior on compartmented or unlicensed data
- treat recommendations as final decisions

## Enforcement Points

Safety is enforced at:

- schema construction
- message routing
- policy decisions
- context building
- reasoning workflows
- explanation generation
- memory writes
- audit logging
- adapter execution
- output redaction
