"""JINX-INTEL summary fusion and impact mapping."""

from jinx.modules.intel.models import (
    IntelligenceFusionResult,
    IntelligenceImpact,
    IntelligenceSummary,
)


class IntelligenceFusionEngine:
    def fuse(self, summaries: tuple[IntelligenceSummary, ...]) -> IntelligenceFusionResult:
        if not summaries:
            raise ValueError("cannot fuse empty intelligence summaries")

        impacts: list[IntelligenceImpact] = []
        for summary in summaries:
            impacts.extend(self._impacts_for_summary(summary))
        return IntelligenceFusionResult(summaries=summaries, impacts=tuple(impacts))

    def _impacts_for_summary(self, summary: IntelligenceSummary) -> tuple[IntelligenceImpact, ...]:
        lowered = summary.summary.lower()
        impacts: list[IntelligenceImpact] = []

        if "weather" in lowered or "visibility" in lowered:
            impacts.append(
                IntelligenceImpact(
                    impacted_area="weather_constraints",
                    summary="Intelligence-derived weather context may affect movement or communications.",
                    confidence=summary.confidence,
                    provenance=summary.provenance,
                )
            )
        if "communications" in lowered or "network" in lowered:
            impacts.append(
                IntelligenceImpact(
                    impacted_area="communications_assumptions",
                    summary="Intelligence-derived context may affect communications assumptions.",
                    confidence=summary.confidence,
                    provenance=summary.provenance,
                )
            )
        if not impacts:
            impacts.append(
                IntelligenceImpact(
                    impacted_area="human_review",
                    summary="Summary requires analyst review before mission impact is inferred.",
                    confidence=summary.confidence,
                    provenance=summary.provenance,
                )
            )
        return tuple(impacts)
