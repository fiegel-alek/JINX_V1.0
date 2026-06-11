# JINX-C5ISR API Contract

This contract describes the current dependency-free C5ISR web API.

All current data paths are synthetic, mock, open, or explicitly authorized. Live adapters are not default behavior.

## Access Model

Development auth uses the `X-JINX-Role` header.

Roles:

- `operator`: submit operator reports and read COP data.
- `c5isr_manager`: submit/review reports, write COP validation, submit INTEL/ISR synthetic inputs, load mission context, inject demo data.
- `commander`: submit human-originated command input and review reports.
- `intel_analyst`: submit INTEL/ISR synthetic inputs and read ISR views.
- `auditor`: read COP/ISR/audit-facing data.
- `system_administrator`: all permissions.

## Read Endpoints

- `GET /api/health`
- `GET /api/cop`
- `GET /api/cop/layers`
- `GET /api/mission-context`
- `GET /api/mission-impacts`
- `GET /api/review-center`
- `GET /api/operator-reports`
- `GET /api/events`
- `GET /api/timeline`
- `GET /api/advisories`
- `GET /api/conflicts`
- `GET /api/recommendations`
- `GET /api/core/analysis-runs`
- `GET /api/core/explanations`
- `GET /api/core/audit`
- `GET /api/core/provenance`
- `GET /api/core/module-boundaries`
- `GET /api/brain/references`
- `GET /api/intelligence-summaries`
- `GET /api/intelligence-impacts`
- `GET /api/isr-feeds`
- `GET /api/human-commands`
- `GET /api/modules`
- `GET /api/sim/c5isr-scenarios`

## Write Endpoints

- `POST /api/operator-reports`
- `POST /api/operator-reports/review`
- `POST /api/cop/tracks/validate`
- `POST /api/mission-context`
- `POST /api/intelligence-summaries`
- `POST /api/isr-feeds`
- `POST /api/brain/query`
- `POST /api/human-commands`
- `POST /api/sim/demo`

## Output Rules

C5ISR outputs remain advisory:

- Conflict packets preserve uncertainty.
- Mission impact packets identify possible affected tasks, routes, areas, and assumptions.
- Recommendations include human review paths and Brain reference IDs.
- Core analysis runs record inputs, consulted modules, confidence bands, output IDs, and human-review requirements.
- Explanation artifacts identify why an output was flagged, contributing inputs, uncertainty, allowed actions, and disallowed actions.
- COP track validation is human-originated.
- ISR feed snapshots are display snapshots only, not collection tasking or live control.

## Current Scenario Packs

- Conflicting location reports
- Communications loss with ISR weather impact
- Delayed movement
- Route hazard
- Medical event
- Stale COP track
- Operator report plus INTEL impact
- NET-related communications issue
