"""Core advisory recommendation generation."""

from jinx.brain.knowledge import DoctrineRepository
from jinx.brain.knowledge.defaults import build_synthetic_doctrine_repository
from jinx.core.reasoning.explanation import CoreExplanationEngine
from jinx.core.schemas import ConflictPacket, Recommendation


class CoreRecommendationEngine:
    def __init__(
        self,
        explanation_engine: CoreExplanationEngine | None = None,
        doctrine_repository: DoctrineRepository | None = None,
    ) -> None:
        self._explanation_engine = explanation_engine or CoreExplanationEngine()
        self._doctrine_repository = doctrine_repository or build_synthetic_doctrine_repository()

    def from_conflict(self, conflict: ConflictPacket) -> Recommendation:
        references = self._references_for_conflict(conflict)
        return Recommendation(
            recommendation_type="human_review_path",
            text=self._text_for_conflict(conflict),
            rationale=self._explanation_engine.recommendation_rationale(conflict),
            assumptions=(
                "Inputs are synthetic or explicitly approved for this shadow-mode workflow.",
                "The conflict packet does not determine which source is correct.",
                *(
                    f"Brain reference available: {reference.title} ({reference.scope.value})."
                    for reference in references
                ),
            ),
            risks=(
                "Proceeding without review may preserve a bad C5ISR assumption.",
                "The synthetic scenario may omit context a human reviewer would consider.",
            ),
            tradeoffs=(
                "Human review adds time but preserves authority and auditability.",
                "Replay helps isolate timing and source-consistency issues.",
            ),
            confidence=conflict.confidence,
            required_human_review=True,
            allowed_actions=conflict.potential_human_resolutions,
            disallowed_actions=(
                "Do not issue operational orders.",
                "Do not modify live systems.",
                "Do not treat the recommendation as a final decision.",
            ),
            provenance_chain=conflict.provenance_chain,
            brain_references=tuple(reference.id for reference in references),
        )

    def _references_for_conflict(self, conflict: ConflictPacket):
        tags = {
            "communications_status_conflict": frozenset({"communications", "review"}),
            "cop_location_conflict": frozenset({"location", "cop", "review"}),
            "cop_status_conflict": frozenset({"mission", "review"}),
            "operator_intel_mission_impact_conflict": frozenset({"mission", "intel", "review"}),
        }.get(conflict.conflict_type, frozenset({"review"}))
        return self._doctrine_repository.search("", tags=tags).matches

    @staticmethod
    def _text_for_conflict(conflict: ConflictPacket) -> str:
        if conflict.conflict_type == "communications_status_conflict":
            return "Review the communications status conflict before relying on affected planning assumptions."
        if conflict.conflict_type == "cop_location_conflict":
            return "Review the COP location conflict and confirm the track before updating mission assumptions."
        if conflict.conflict_type == "cop_status_conflict":
            return "Review the conflicting status reports before treating the track state as current."
        if conflict.conflict_type == "operator_intel_mission_impact_conflict":
            return "Review operator and INTEL-derived mission impacts together before changing assumptions."
        return "Review the C5ISR conflict packet before relying on affected assumptions."
