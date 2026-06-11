"""Core advisory reasoning workflows."""

from dataclasses import dataclass

from jinx.bus import FabricMessage, MessageRouter, RouteResult
from jinx.common.types import DataMode
from jinx.core.reasoning.detector import CoreConflictDetector
from jinx.core.reasoning.models import CoreAnalysisRun, ExplanationArtifact, confidence_summary_from_score
from jinx.core.reasoning.recommender import CoreRecommendationEngine
from jinx.core.schemas import ConflictPacket, Event, Recommendation


@dataclass(frozen=True, slots=True)
class CoreReasoningResult:
    conflicts: tuple[ConflictPacket, ...]
    recommendations: tuple[Recommendation, ...]
    route_results: tuple[RouteResult, ...]
    explanations: tuple[ExplanationArtifact, ...] = ()
    analysis_run: CoreAnalysisRun | None = None


class CoreReasoningWorkflow:
    def __init__(
        self,
        router: MessageRouter,
        conflict_detector: CoreConflictDetector | None = None,
        recommendation_engine: CoreRecommendationEngine | None = None,
    ) -> None:
        self._router = router
        self._conflict_detector = conflict_detector or CoreConflictDetector()
        self._recommendation_engine = recommendation_engine or CoreRecommendationEngine()

    def review_events(
        self, events: tuple[Event, ...], destination: str = "jinx-c5isr"
    ) -> CoreReasoningResult:
        conflicts = self._conflict_detector.detect(events)
        recommendations = tuple(self._recommendation_engine.from_conflict(item) for item in conflicts)
        route_results: list[RouteResult] = []

        for conflict in conflicts:
            route_results.append(self._router.route(self._conflict_message(conflict, destination)))
        for recommendation in recommendations:
            route_results.append(
                self._router.route(self._recommendation_message(recommendation, destination))
            )

        explanations = self._explanations(conflicts, recommendations)
        analysis_run = self._analysis_run(events, conflicts, recommendations)
        return CoreReasoningResult(
            conflicts,
            recommendations,
            tuple(route_results),
            explanations=explanations,
            analysis_run=analysis_run,
        )

    @staticmethod
    def _explanations(
        conflicts: tuple[ConflictPacket, ...],
        recommendations: tuple[Recommendation, ...],
    ) -> tuple[ExplanationArtifact, ...]:
        artifacts: list[ExplanationArtifact] = []
        for conflict in conflicts:
            artifacts.append(
                ExplanationArtifact(
                    output_id=conflict.id,
                    output_type="conflict_packet",
                    why_flagged=conflict.explanation,
                    contributing_inputs=conflict.conflicting_items,
                    brain_references=(),
                    uncertainty="Core preserved conflicting claims and did not decide truth.",
                    recommended_review_role=conflict.recommended_review_role,
                    allowed_actions=conflict.potential_human_resolutions,
                    disallowed_actions=(
                        "Do not issue operational orders.",
                        "Do not treat this as a final decision.",
                    ),
                )
            )
        for recommendation in recommendations:
            artifacts.append(
                ExplanationArtifact(
                    output_id=recommendation.id,
                    output_type="recommendation",
                    why_flagged=recommendation.rationale,
                    contributing_inputs=tuple(record.source for record in recommendation.provenance_chain),
                    brain_references=recommendation.brain_references,
                    uncertainty="Recommendation remains advisory and requires human review.",
                    recommended_review_role="human reviewer",
                    allowed_actions=recommendation.allowed_actions,
                    disallowed_actions=recommendation.disallowed_actions,
                )
            )
        return tuple(artifacts)

    @staticmethod
    def _analysis_run(
        events: tuple[Event, ...],
        conflicts: tuple[ConflictPacket, ...],
        recommendations: tuple[Recommendation, ...],
    ) -> CoreAnalysisRun:
        scores = [item.confidence for item in (*conflicts, *recommendations)]
        score = scores[0] if scores else events[0].confidence
        return CoreAnalysisRun(
            input_ids=tuple(event.id for event in events),
            modules_consulted=("jinx-core", "jinx-brain", "jinx-c5isr"),
            confidence_summary=confidence_summary_from_score(score),
            output_ids=tuple(item.id for item in (*conflicts, *recommendations)),
            human_review_required=True,
        )

    @staticmethod
    def _conflict_message(conflict: ConflictPacket, destination: str) -> FabricMessage:
        return FabricMessage(
            source_module="jinx-core",
            destination=destination,
            payload_schema="conflict_packet.v1",
            schema_version="1.0",
            sensitivity_label="synthetic",
            license_scope="core",
            provenance_ref=conflict.id,
            payload={
                "id": conflict.id,
                "conflict_type": conflict.conflict_type,
                "explanation": conflict.explanation,
                "confidence": str(conflict.confidence.value),
                "human_review_role": conflict.recommended_review_role,
                "likely_impacts": list(conflict.likely_impacts),
                "potential_human_resolutions": list(conflict.potential_human_resolutions),
            },
            data_mode=DataMode.SYNTHETIC,
        )

    @staticmethod
    def _recommendation_message(recommendation: Recommendation, destination: str) -> FabricMessage:
        return FabricMessage(
            source_module="jinx-core",
            destination=destination,
            payload_schema="recommendation.v1",
            schema_version="1.0",
            sensitivity_label="synthetic",
            license_scope="core",
            provenance_ref=recommendation.id,
            payload={
                "id": recommendation.id,
                "recommendation_type": recommendation.recommendation_type,
                "text": recommendation.text,
                "confidence": str(recommendation.confidence.value),
                "required_human_review": str(recommendation.required_human_review),
                "allowed_actions": list(recommendation.allowed_actions),
                "brain_references": list(recommendation.brain_references),
            },
            data_mode=DataMode.SYNTHETIC,
        )
