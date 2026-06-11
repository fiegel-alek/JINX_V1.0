"""Core advisory recommendation generation."""

from jinx.core.reasoning.explanation import CoreExplanationEngine
from jinx.core.schemas import ConflictPacket, Recommendation


class CoreRecommendationEngine:
    def __init__(self, explanation_engine: CoreExplanationEngine | None = None) -> None:
        self._explanation_engine = explanation_engine or CoreExplanationEngine()

    def from_conflict(self, conflict: ConflictPacket) -> Recommendation:
        return Recommendation(
            recommendation_type="human_review_path",
            text=(
                "Review the communications status conflict and run the synthetic replay "
                "before relying on the affected planning assumption."
            ),
            rationale=self._explanation_engine.recommendation_rationale(conflict),
            assumptions=(
                "Inputs are synthetic or explicitly approved for this shadow-mode workflow.",
                "The conflict packet does not determine which source is correct.",
            ),
            risks=(
                "Proceeding without review may preserve a bad communications assumption.",
                "The synthetic scenario may omit context a human reviewer would consider.",
            ),
            tradeoffs=(
                "Human review adds time but preserves authority and auditability.",
                "Replay helps isolate timing and source-consistency issues.",
            ),
            confidence=conflict.confidence,
            required_human_review=True,
            allowed_actions=(
                "Request human review.",
                "Run a synthetic replay.",
                "Annotate affected planning assumptions.",
            ),
            disallowed_actions=(
                "Do not issue operational orders.",
                "Do not modify live systems.",
                "Do not treat the recommendation as a final decision.",
            ),
            provenance_chain=conflict.provenance_chain,
        )
