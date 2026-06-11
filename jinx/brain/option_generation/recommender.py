"""Human-review recommendation generation."""

from jinx.brain.explanation import ExplanationEngine
from jinx.core.schemas import ConflictPacket, Recommendation


class RecommendationEngine:
    def __init__(self, explanation_engine: ExplanationEngine | None = None) -> None:
        self._explanation_engine = explanation_engine or ExplanationEngine()

    def from_conflict(self, conflict: ConflictPacket) -> Recommendation:
        return Recommendation(
            recommendation_type="human_review_path",
            text=(
                "Review the communications status conflict and run the synthetic replay "
                "before relying on the affected planning assumption."
            ),
            rationale=self._explanation_engine.recommendation_rationale(conflict),
            assumptions=(
                "Inputs are synthetic and intended for shadow-mode validation.",
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
