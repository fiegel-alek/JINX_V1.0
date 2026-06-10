# JINX

Joint Integrated Network eXecutive

JINX is a vendor-agnostic cognitive integration layer that augments, feeds, and coheres existing systems without replacing them.

This repository is being rebuilt as a simulation-first, advisory, human-in-the-loop platform. The early codebase prioritizes safe interfaces, strict schemas, provenance, auditability, module boundaries, and synthetic data over live integrations.

## Non-Negotiable Guardrails

1. JINX is advisory only.
2. JINX never issues operational orders.
3. JINX never controls weapons or physical effects.
4. JINX never performs autonomous targeting.
5. JINX never retasks intelligence collection assets.
6. JINX never hides uncertainty.
7. JINX preserves provenance for important information.
8. JINX shows confidence levels for assessments.
9. JINX explains why it flagged, ranked, or recommended something.
10. JINX uses synthetic, mock, open, or explicitly authorized data only.
11. JINX supports strict module licensing boundaries.
12. JINX modules must not leak information, inference, or learned behavior across unlicensed domains.
13. JINX is built for simulation and shadow-mode operation before real-world integration.
14. JINX treats real-world feed adapters as controlled plugins, never as default behavior.

## Phase 0 Focus

- Core schemas for advisory outputs, confidence, provenance, and audit records.
- A module registry with licensing and capability metadata.
- A conservative policy engine for routing, recommendations, adapter use, and memory writes.
- A cognitive boundary layer for entitlement-aware redaction.
- Synthetic scenario and message primitives.
- Tests that encode safety behavior before higher-level features are added.

## Repository Layout

```text
docs/
  architecture/
jinx/
  core/
  boundary/
  bus/
  modules/
  adapters/
  common/
tests/
```

## Running Tests

```bash
python3 -m unittest discover -s tests
```

## Development Posture

Build mock and simulation paths first. Real adapters must be explicit, permissioned, audited, and never allowed to bypass JINX-Core.
