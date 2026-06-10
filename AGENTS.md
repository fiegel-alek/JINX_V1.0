# JINX Development Guide

This codebase follows the JINX project brief and guardrails.

## Safety Posture

- Build advisory workflows only.
- Do not add autonomous command, targeting, weapons-control, intelligence-collection tasking, or physical-effect control behavior.
- Default to synthetic, mock, open, or explicitly authorized data.
- Every meaningful assessment must preserve provenance, confidence, and explanation fields.
- New cross-module communication must pass through policy and boundary checks.
- Real-world adapters must be explicit plugins with permissions and audit logging.

## Engineering Posture

- Prefer strict typed schemas over loose dictionaries.
- Keep modules isolated by license scope and domain.
- Add tests for any new boundary, policy, audit, provenance, or advisory behavior.
- Avoid introducing live integrations until simulation behavior is complete and tested.
