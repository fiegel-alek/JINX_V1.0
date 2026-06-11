"""BRAIN reasoning workflows."""

from dataclasses import dataclass

from jinx.brain.conflict_resolution import ConflictDetector
from jinx.brain.option_generation import RecommendationEngine
from jinx.bus import FabricMessage, MessageRouter, RouteResult
from jinx.common.types import DataMode
from jinx.core.schemas import ConflictPacket, Event, Recommendation


@dataclass(frozen=True, slots=True)
class ReasoningResult:
    conflicts: tuple[ConflictPacket, ...]
    recommendations: tuple[Recommendation, ...]
    route_results: tuple[RouteResult, ...]


class BrainReasoningWorkflow:
    def __init__(
        self,
        router: MessageRouter,
        conflict_detector: ConflictDetector | None = None,
        recommendation_engine: RecommendationEngine | None = None,
    ) -> None:
        self._router = router
        self._conflict_detector = conflict_detector or ConflictDetector()
        self._recommendation_engine = recommendation_engine or RecommendationEngine()

    def review_events(self, events: tuple[Event, ...], destination: str = "jinx-core") -> ReasoningResult:
        conflicts = self._conflict_detector.detect(events)
        recommendations = tuple(self._recommendation_engine.from_conflict(item) for item in conflicts)
        route_results: list[RouteResult] = []

        for conflict in conflicts:
            route_results.append(self._router.route(self._conflict_message(conflict, destination)))
        for recommendation in recommendations:
            route_results.append(
                self._router.route(self._recommendation_message(recommendation, destination))
            )

        return ReasoningResult(conflicts, recommendations, tuple(route_results))

    @staticmethod
    def _conflict_message(conflict: ConflictPacket, destination: str) -> FabricMessage:
        return FabricMessage(
            source_module="jinx-brain",
            destination=destination,
            payload_schema="conflict_packet.v1",
            schema_version="1.0",
            sensitivity_label="synthetic",
            license_scope="brain",
            provenance_ref=conflict.id,
            payload={
                "id": conflict.id,
                "conflict_type": conflict.conflict_type,
                "explanation": conflict.explanation,
                "confidence": str(conflict.confidence.value),
                "human_review_role": conflict.recommended_review_role,
            },
            data_mode=DataMode.SYNTHETIC,
        )

    @staticmethod
    def _recommendation_message(recommendation: Recommendation, destination: str) -> FabricMessage:
        return FabricMessage(
            source_module="jinx-brain",
            destination=destination,
            payload_schema="recommendation.v1",
            schema_version="1.0",
            sensitivity_label="synthetic",
            license_scope="brain",
            provenance_ref=recommendation.id,
            payload={
                "id": recommendation.id,
                "recommendation_type": recommendation.recommendation_type,
                "text": recommendation.text,
                "confidence": str(recommendation.confidence.value),
                "required_human_review": str(recommendation.required_human_review),
            },
            data_mode=DataMode.SYNTHETIC,
        )
