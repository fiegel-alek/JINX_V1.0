# Module Boundaries

JINX modules are licensed, permissioned, and bounded. A module may only receive approved fields and may only emit outputs that fit its entitlements.

## Core Rule

No module should infer, expose, store, or learn from unlicensed domain information.

## Boundary Types

- Data containment: fields are removed or generalized before entering a module.
- Inference containment: causal explanations are masked when they would reveal unlicensed domains.
- Learning containment: feedback and learned patterns remain scoped to entitled compartments.
- Output containment: recommendations are redacted before they expose unlicensed capabilities.

## Example

If JINX-NET is not licensed, another module should not receive:

```text
Likely TDMA timeslot conflict due to network geometry.
```

It may receive:

```text
Communications issue detected. Network-domain review recommended.
```
