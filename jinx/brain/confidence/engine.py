"""Confidence support for JINX-BRAIN outputs."""

from jinx.brain.context_builder import BoundedBrainContext
from jinx.brain.knowledge import DoctrineRecord
from jinx.common.types.confidence import ConfidenceScore


class BrainConfidenceEngine:
    def assess(
        self,
        references: tuple[DoctrineRecord, ...],
        context: BoundedBrainContext | None = None,
    ) -> ConfidenceScore:
        source_quality = 0.7 if references else 0.35
        recency = 0.65
        corroboration = min(0.9, 0.2 + 0.18 * len(references))
        contradiction = 0.25 if context and context.redactions else 0.1
        completeness = 0.75 if context and len(context.context) >= 3 else 0.45
        value = max(
            0.05,
            min(
                0.95,
                (source_quality * 0.28)
                + (recency * 0.14)
                + (corroboration * 0.22)
                + ((1 - contradiction) * 0.16)
                + (completeness * 0.20),
            ),
        )
        rationale = "BRAIN confidence combines references, bounded context completeness, and redaction risk."
        if context and context.redactions:
            rationale += " Boundary redactions reduce confidence."
        return ConfidenceScore(
            value=round(value, 2),
            scale="0.0-1.0",
            rationale=rationale,
            source_quality=round(source_quality, 2),
            recency_factor=round(recency, 2),
            corroboration_factor=round(corroboration, 2),
            contradiction_factor=round(contradiction, 2),
            completeness_factor=round(completeness, 2),
        )
