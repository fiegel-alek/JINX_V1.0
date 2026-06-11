# Phase 3 Application Spine

Phase 3 turns the library skeleton into an application-oriented architecture while staying simulation-first and advisory-only.

## Added Components

- Identity and RBAC primitives.
- Runtime configuration model.
- JSON document store for early persistence.
- Core memory stores for audit and provenance.
- Application service layer for Operator Mini, C5ISR, Core, and BUS coordination.
- Dependency-free API handler layer for early integration tests.
- Simulation replay frames.
- Controlled adapter gates.
- GitHub Actions unit-test workflow.
- SQLite-backed API persistence.
- HTTP server with optional TLS wrapping for HTTPS deployment.
- Static COP frontend served from the same web layer.

## Command Authority Rule

Core may carry, route, validate, and audit human-originated command input. Core must never generate command authority. Tests enforce that Operator Mini can submit `human_command.v1` while Core cannot originate it.

## Future Production Work

- Replace JSON store with a real database layer.
- Add authenticated HTTP APIs.
- Add production TLS/certificate management.
- Add durable queues and subscriptions.
- Add UI clients for Core, C5ISR, Operator Mini, NET, INTEL, and SIM.
- Add structured logging, migrations, and deployment packaging.
