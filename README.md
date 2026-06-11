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

## Current Phase 1 Capabilities

- Policy-enforced message routing with audit records and dead-letter handling.
- Default manifests for Core, BUS, BRAIN, C5ISR, NET, INTEL, and SIM.
- Synthetic communications-conflict scenario generation.
- Core conflict detection for synthetic communications status contradictions.
- Core human-review recommendation generation from conflict packets.
- BRAIN doctrine, TACSOP, and SOP knowledge-reference primitives.
- Proposed JINX-Operator Mini edge-client schemas for operator reports and C5ISR advisories.
- Human-originated command carrier schema that Core cannot generate.
- C5ISR COP state management primitives.
- Boundary-aware message redaction in the router.
- Synthetic JINX-NET MTDL validation stubs.
- Synthetic/authorized JINX-INTEL summary fusion and impact mapping.
- In-memory audit and provenance stores.
- Phase 3 application service layer and dependency-free API handlers.
- Identity/RBAC primitives and default roles.
- JSON document persistence for early app wiring.
- Simulation replay frames.
- Controlled adapter gates.
- GitHub Actions unit-test workflow.
- SQLite-backed web/API persistence.
- HTTP server with optional TLS certificate support for HTTPS.
- First static C5ISR COP interface.
- End-to-end tests for synthetic event reasoning through policy and bus routing.

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

## Running The Web/COP Prototype

```bash
python3 -m jinx.web --host 127.0.0.1 --port 8080 --database data/jinx.sqlite3
```

Open `http://127.0.0.1:8080`.

For HTTPS in a controlled environment, provide a certificate and key:

```bash
python3 -m jinx.web --certfile path/to/cert.pem --keyfile path/to/key.pem
```

## Development Posture

Build mock and simulation paths first. Real adapters must be explicit, permissioned, audited, and never allowed to bypass JINX-Core.
