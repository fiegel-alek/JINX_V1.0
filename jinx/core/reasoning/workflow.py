"""Core advisory reasoning workflows."""

from dataclasses import dataclass

from jinx.bus import FabricMessage, MessageRouter, RouteResult
from jinx.common.types import DataMode
from jinx.core.reasoning.detector import CoreConflictDetector
from jinx.core.reasoning.recommender import CoreRecommendationEngine
from jinx.core.schemas import ConflictPacket, Event, Recommendation


@dataclass(frozen=True, slots=True)
class CoreReasoningResult:
    conflicts: tuple[ConflictPacket, ...]
    recommendations: tuple[Recommendation, ...]
    route_results: tuple[RouteResult, ...]


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

        return CoreReasoningResult(conflicts, recommendations, tuple(route_results))

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
            },
            data_mode=DataMode.SYNTHETIC,
        )
