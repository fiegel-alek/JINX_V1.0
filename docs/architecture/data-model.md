# Data Model

Phase 0 defines small, strict core objects that later modules can compose.

## ConfidenceScore

Captures value, scale, rationale, and contributing factors such as source quality, recency, corroboration, contradiction, and completeness.

## ProvenanceRecord

Tracks the source, received time, processing module, transformations, confidence, and downstream outputs for important information.

## AdvisoryOutput

Represents an observation, assessment, warning, recommendation, simulation result, confidence-limited inference, or human-review-required output. It must include confidence, explanation, provenance, and explicit allowed/disallowed action fields.

## AuditRecord

Append-only record of inputs, outputs, module calls, policy decisions, redactions, confidence changes, user overrides, simulation events, and adapter usage.

## ModuleManifest

Declares module identity, license scope, permissions, allowed inputs, allowed outputs, capabilities, dependencies, safety classification, and simulation support.
