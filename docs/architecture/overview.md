# JINX Architecture Overview

JINX is a vendor-agnostic cognitive integration platform. It augments existing systems by absorbing information from bounded sources, reasoning across approved domains, detecting conflicts, simulating outcomes, and returning coherent, explainable advisory outputs.

JINX does not replace existing systems and must not become an autonomous authority layer.

## Major Components

- JINX-Core: the main AI processing, analysis, orchestration, policy, provenance, audit, and task-execution center.
- JINX-BRAIN: doctrine, TACSOP, SOP, and mission-knowledge reference subsystem that feeds Core.
- JINX-NET: Multi-Tactical Data Link network management, validation, and issue-correction module.
- JINX-C5ISR: COP management, potential threat detection, ISR fusion, and warfighter/operator impact awareness.
- JINX-INTEL: intelligence fusion, incorporation, contextualization, and correlation module.
- JINX-SIM: synthetic scenarios, replay, injects, expected outcomes, and test comparison.
- JINX-BUS / JINX-FABRIC: tactical-radio and external integration fabric, simulation-first until explicit access exists.
- JINX-Operator Mini: proposed edge client for operator reports and C5ISR advisories.
- Cognitive Boundary Layer: entitlement-aware containment for data, inference, learning, and outputs.
- Adapter Framework: permissioned external connectors that cannot bypass Core.

## Runtime Principle

JINX-Core is the main system. JINX-BRAIN feeds Core with approved doctrine, TACSOP, SOP, and mission knowledge. NET, INTEL, C5ISR, SIM, and BUS/FABRIC can be separated as licensed modules or bundled as a larger package. Cross-module outputs still pass through Core policy, provenance, audit, and boundary checks.

## Initial Build Principle

Phase 0 is intentionally simulation-first. It creates safe contracts before real integrations:

- strict schemas
- synthetic data labels
- advisory output labels
- provenance records
- confidence scores
- append-only audit events
- module entitlements
- boundary redaction
- focused tests

## Phase 1 Spine

The current implementation adds the first vertical reasoning path:

1. JINX-SIM creates synthetic communications status events.
2. JINX-Core detects a bounded conflict without deciding truth.
3. JINX-Core emits a confidence-rated conflict packet and human-review recommendation.
4. JINX-BUS routes both through JINX-Core policy checks.
5. The audit layer records policy and routing decisions.
