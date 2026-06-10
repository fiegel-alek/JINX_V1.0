"""Simple entitlement-aware redaction for Phase 0."""

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class BoundaryResult:
    payload: dict[str, object]
    redacted_fields: tuple[str, ...]
    explanation: str


class EntitlementBoundary:
    def redact(
        self,
        payload: Mapping[str, object],
        allowed_fields: frozenset[str],
        abstract_replacements: Mapping[str, object] | None = None,
    ) -> BoundaryResult:
        abstract_replacements = abstract_replacements or {}
        redacted_fields: list[str] = []
        output: dict[str, object] = {}

        for key, value in payload.items():
            if key in allowed_fields:
                output[key] = value
            elif key in abstract_replacements:
                output[key] = abstract_replacements[key]
                redacted_fields.append(key)
            else:
                redacted_fields.append(key)

        explanation = "no redaction required"
        if redacted_fields:
            explanation = "payload redacted to preserve module entitlement boundaries"

        return BoundaryResult(output, tuple(redacted_fields), explanation)
