# JINX-Operator Mini

JINX-Operator Mini is a proposed edge client for warfighters and operators on the ground.

It is not a command system. It is a reporting and advisory interface that can communicate with JINX-C5ISR when authorized. Its purpose is to reduce cognitive load, preserve context, and help operators send structured observations while receiving confidence-limited situational advisories.

## Primary Functions

- Submit position, status, communications, medical, logistics, hazard, and observation reports.
- Attach provenance and confidence metadata to field reports.
- Receive C5ISR-generated COP advisories and human-review prompts.
- Operate in simulation and disconnected/mock modes first.

## Prohibited Functions

JINX-Operator Mini must not:

- receive or display autonomous orders from JINX
- request or authorize targeting
- control weapons or physical effects
- retask ISR or intelligence collection assets
- bypass human command authority
- hide uncertainty or provenance

## Communication Pattern

```text
Operator Mini -> C5ISR -> Core -> C5ISR -> Operator Mini
```

C5ISR is the direct interface for the operator-facing client. Core performs the main advisory analysis. BRAIN may provide doctrine/SOP references to Core. BUS/FABRIC remains simulation-first unless explicit tactical-radio access is authorized.

## Phase 1 Implementation

- `OperatorReport` schema for synthetic field reports.
- `COPAdvisory` schema for C5ISR-to-operator advisory output.
- C5ISR intake workflow that converts operator reports into domain-neutral events.
- Tests proving advisory-only behavior and rejection of prohibited command language.
