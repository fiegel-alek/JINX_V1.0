"""High-level application orchestration services."""

from dataclasses import dataclass
from datetime import UTC, datetime

from jinx.bus import FabricMessage, MessageRouter, RouteResult
from jinx.common.types import DataMode
from jinx.core.audit import AuditLog
from jinx.core.policy import PolicyEngine
from jinx.core.persistence import SQLiteJINXDatabase
from jinx.core.reasoning import CoreReasoningWorkflow
from jinx.core.registry import build_default_registry
from jinx.core.schemas import ConflictPacket, Event, HumanCommandInput, OperatorReport, Recommendation
from jinx.modules.c5isr import C5ISRIntakeResult, C5ISRReportIntake, COPManager
from jinx.modules.intel import IntelligenceFusionEngine, IntelligenceFusionResult, IntelligenceSummary, ISRFeedSnapshot


@dataclass(frozen=True, slots=True)
class OperatorReportResult:
    intake: C5ISRIntakeResult
    report_route: RouteResult
    advisory_route: RouteResult
    core_analysis: object | None = None


@dataclass(frozen=True, slots=True)
class IntelligenceIngestResult:
    fusion: IntelligenceFusionResult
    impact_routes: tuple[RouteResult, ...]
    core_analysis: object | None = None


class JINXApplicationService:
    def __init__(
        self,
        router: MessageRouter | None = None,
        database: SQLiteJINXDatabase | None = None,
    ) -> None:
        self.audit_log = AuditLog()
        self.router = router or MessageRouter(PolicyEngine(build_default_registry()), self.audit_log)
        self.database = database
        self.c5isr_intake = C5ISRReportIntake()
        self.cop_manager = COPManager(name="jinx-phase3-cop")
        self.core_reasoning = CoreReasoningWorkflow(self.router)
        self.intel_fusion = IntelligenceFusionEngine()
        self._events: list[Event] = []

    def submit_operator_report(self, report: OperatorReport) -> OperatorReportResult:
        report_route = self.router.route(
            FabricMessage(
                source_module="jinx-operator-mini",
                destination="jinx-c5isr",
                payload_schema="operator_report.v1",
                schema_version="1.0",
                sensitivity_label="synthetic",
                license_scope="operator-mini",
                provenance_ref=report.id,
                payload={"id": report.id, "summary": report.summary, "reporter_id": report.reporter_id},
                data_mode=report.data_mode,
            )
        )
        intake = self.c5isr_intake.ingest_operator_report(report)
        if intake.event.location is not None:
            self.cop_manager.apply_event(intake.event)
        advisory_route = self.router.route(
            FabricMessage(
                source_module="jinx-c5isr",
                destination="jinx-operator-mini",
                payload_schema="cop_advisory.v1",
                schema_version="1.0",
                sensitivity_label="synthetic",
                license_scope="c5isr",
                provenance_ref=intake.advisory.id,
                payload={"id": intake.advisory.id, "summary": intake.advisory.summary},
                data_mode=DataMode.SYNTHETIC,
            )
        )
        self._events.append(intake.event)
        self._persist_operator_report(report, intake, report_route, advisory_route)
        core_analysis = self._run_core_analysis()
        return OperatorReportResult(
            intake=intake,
            report_route=report_route,
            advisory_route=advisory_route,
            core_analysis=core_analysis,
        )

    def submit_human_command(self, command: HumanCommandInput) -> RouteResult:
        result = self.router.route(
            FabricMessage(
                source_module="jinx-operator-mini",
                destination=command.target_module,
                payload_schema="human_command.v1",
                schema_version="1.0",
                sensitivity_label="synthetic",
                license_scope="operator-mini",
                provenance_ref=command.id,
                payload={
                    "id": command.id,
                    "text": command.text,
                    "issuing_user_id": command.issuing_user_id,
                    "issuing_role": command.issuing_role,
                },
                data_mode=command.data_mode,
            )
        )
        if self.database is not None:
            self.database.save_document(
                "human_commands",
                command.id,
                {
                    "id": command.id,
                    "issuing_user_id": command.issuing_user_id,
                    "issuing_role": command.issuing_role,
                    "target_module": command.target_module,
                    "text": command.text,
                    "delivered": result.delivered,
                    "data_mode": command.data_mode.value,
                },
            )
        return result

    def ingest_intelligence_summary(self, summary: IntelligenceSummary) -> IntelligenceIngestResult:
        fusion = self.intel_fusion.fuse((summary,))
        impact_routes: list[RouteResult] = []
        events: list[Event] = []
        for impact in fusion.impacts:
            impact_routes.append(
                self.router.route(
                    FabricMessage(
                        source_module="jinx-intel",
                        destination="jinx-core",
                        payload_schema="intel_impact.v1",
                        schema_version="1.0",
                        sensitivity_label="synthetic",
                        license_scope="intel",
                        provenance_ref=impact.id,
                        payload={
                            "id": impact.id,
                            "impacted_area": impact.impacted_area,
                            "summary": impact.summary,
                            "confidence": impact.confidence.value,
                        },
                        data_mode=summary.data_mode,
                        confidence=impact.confidence,
                    )
                )
            )
            event = self.c5isr_intake.ingest_intel_impact(impact, summary.id)
            events.append(event)
            self._events.append(event)

        self._persist_intelligence_summary(summary, fusion, tuple(impact_routes), tuple(events))
        core_analysis = self._run_core_analysis()
        return IntelligenceIngestResult(fusion=fusion, impact_routes=tuple(impact_routes), core_analysis=core_analysis)

    def ingest_isr_feed_snapshot(self, snapshot: ISRFeedSnapshot) -> RouteResult:
        result = self.router.route(
            FabricMessage(
                source_module="jinx-intel",
                destination="jinx-bus",
                payload_schema="isr_feed.v1",
                schema_version="1.0",
                sensitivity_label="synthetic",
                license_scope="intel",
                provenance_ref=snapshot.id,
                payload={
                    "id": snapshot.id,
                    "feed_name": snapshot.feed_name,
                    "feed_type": snapshot.feed_type,
                    "status": snapshot.status,
                    "coverage_area": snapshot.coverage_area,
                    "summary": snapshot.summary,
                    "confidence": snapshot.confidence.value,
                    "data_mode": snapshot.data_mode.value,
                },
                data_mode=snapshot.data_mode,
                confidence=snapshot.confidence,
            )
        )
        if self.database is not None:
            self.database.save_document(
                "isr_feeds",
                snapshot.id,
                {
                    "id": snapshot.id,
                    "feed_name": snapshot.feed_name,
                    "feed_type": snapshot.feed_type,
                    "status": snapshot.status,
                    "coverage_area": snapshot.coverage_area,
                    "summary": snapshot.summary,
                    "confidence": snapshot.confidence.value,
                    "data_mode": snapshot.data_mode.value,
                    "restrictions": list(snapshot.restrictions),
                    "related_entities": list(snapshot.related_entities),
                    "related_locations": list(snapshot.related_locations),
                    "simulation_flag": snapshot.simulation_flag,
                    "delivered_to_bus": result.delivered,
                    "timestamp": snapshot.timestamp.isoformat(),
                },
            )
        return result

    def review_operator_report(
        self,
        report_id: str,
        state: str,
        reviewer_id: str,
        note: str = "",
    ) -> dict[str, object]:
        if self.database is None:
            raise ValueError("database is required for report review")
        allowed_states = frozenset({"new", "under_review", "validated", "needs_more_info", "closed"})
        if state not in allowed_states:
            raise ValueError(f"invalid report review state: {state}")
        if not reviewer_id:
            raise ValueError("reviewer_id is required")

        report = self.database.get_document("operator_reports", report_id)
        history = list(report.get("review_history", []))
        history.append(
            {
                "state": state,
                "reviewer_id": reviewer_id,
                "note": note,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        report["review_state"] = state
        report["reviewed_by"] = reviewer_id
        report["review_note"] = note
        report["review_history"] = history
        self.database.save_document("operator_reports", report_id, report)
        return report

    def cop_state_document(self) -> dict[str, object]:
        state = self.cop_manager.state()
        reports = self.database.list_documents("operator_reports") if self.database else ()
        advisories = self.database.list_documents("cop_advisories") if self.database else ()
        return {
            "id": state.id,
            "name": state.name,
            "data_mode": state.data_mode.value,
            "tracks": [
                {
                    "entity_id": track.entity.id,
                    "label": track.entity.label,
                    "entity_type": track.entity.entity_type,
                    "location": track.location.label,
                    "status": track.status,
                    "confidence": track.confidence.value,
                    "last_report_id": track.last_report_id,
                    "updated_at": track.updated_at.isoformat(),
                    "report_count": sum(1 for report in reports if report.get("reporter_id") == track.entity.id),
                    "advisory_count": sum(
                        1
                        for advisory in advisories
                        if track.last_report_id in advisory.get("related_report_ids", [])
                    ),
                    "stale": False,
                }
                for track in state.tracks
            ],
        }

    def _persist_operator_report(
        self,
        report: OperatorReport,
        intake: C5ISRIntakeResult,
        report_route: RouteResult,
        advisory_route: RouteResult,
    ) -> None:
        if self.database is None:
            return
        self.database.save_document(
            "operator_reports",
            report.id,
            {
                "id": report.id,
                "report_type": report.report_type.value,
                "reporter_id": report.reporter_id,
                "source_device_id": report.source_device_id,
                "summary": report.summary,
                "location": report.location.label if report.location else None,
                "confidence": report.confidence.value,
                "delivered": report_route.delivered,
                "data_mode": report.data_mode.value,
                "review_state": "new",
                "reviewed_by": None,
                "review_note": "",
                "review_history": [],
            },
        )
        self.database.save_document(
            "events",
            intake.event.id,
            {
                "id": intake.event.id,
                "event_type": intake.event.event_type.value,
                "source": intake.event.source,
                "description": intake.event.description,
                "location": intake.event.location.label if intake.event.location else None,
                "confidence": intake.event.confidence.value,
                "operator_report_id": report.id,
            },
        )
        self.database.save_document(
            "cop_advisories",
            intake.advisory.id,
            {
                "id": intake.advisory.id,
                "recipient_id": intake.advisory.recipient_id,
                "summary": intake.advisory.summary,
                "confidence": intake.advisory.confidence.value,
                "related_report_ids": list(intake.advisory.related_report_ids),
                "delivered": advisory_route.delivered,
            },
        )
        if intake.event.location is not None:
            self.database.save_document("cop_states", "latest", self.cop_state_document())

    def _run_core_analysis(self) -> object | None:
        if not self._events:
            return None
        result = self.core_reasoning.review_events(tuple(self._events))
        self._persist_core_analysis(result.conflicts, result.recommendations)
        return result

    def _persist_core_analysis(
        self,
        conflicts: tuple[ConflictPacket, ...],
        recommendations: tuple[Recommendation, ...],
    ) -> None:
        if self.database is None:
            return
        for conflict in conflicts:
            self.database.save_document(
                "conflicts",
                conflict.id,
                {
                    "id": conflict.id,
                    "conflict_type": conflict.conflict_type,
                    "detected_by_module": conflict.detected_by_module,
                    "conflicting_items": list(conflict.conflicting_items),
                    "likely_impacts": list(conflict.likely_impacts),
                    "potential_human_resolutions": list(conflict.potential_human_resolutions),
                    "confidence": conflict.confidence.value,
                    "explanation": conflict.explanation,
                    "recommended_review_role": conflict.recommended_review_role,
                    "simulation_replay_available": conflict.simulation_replay_available,
                    "timestamp": conflict.timestamp.isoformat(),
                },
            )
        for recommendation in recommendations:
            self.database.save_document(
                "recommendations",
                recommendation.id,
                {
                    "id": recommendation.id,
                    "recommendation_type": recommendation.recommendation_type,
                    "text": recommendation.text,
                    "rationale": recommendation.rationale,
                    "assumptions": list(recommendation.assumptions),
                    "risks": list(recommendation.risks),
                    "tradeoffs": list(recommendation.tradeoffs),
                    "confidence": recommendation.confidence.value,
                    "required_human_review": recommendation.required_human_review,
                    "allowed_actions": list(recommendation.allowed_actions),
                    "disallowed_actions": list(recommendation.disallowed_actions),
                    "brain_references": list(recommendation.brain_references),
                },
            )

    def _persist_intelligence_summary(
        self,
        summary: IntelligenceSummary,
        fusion: IntelligenceFusionResult,
        routes: tuple[RouteResult, ...],
        events: tuple[Event, ...],
    ) -> None:
        if self.database is None:
            return
        self.database.save_document(
            "intelligence_summaries",
            summary.id,
            {
                "id": summary.id,
                "source_category": summary.source_category,
                "summary": summary.summary,
                "reliability": summary.reliability,
                "confidence": summary.confidence.value,
                "data_mode": summary.data_mode.value,
                "restrictions": list(summary.restrictions),
                "related_entities": list(summary.related_entities),
                "related_locations": list(summary.related_locations),
                "simulation_flag": summary.simulation_flag,
                "timestamp": summary.timestamp.isoformat(),
            },
        )
        delivered_by_impact = {route.message.provenance_ref: route.delivered for route in routes}
        for impact in fusion.impacts:
            self.database.save_document(
                "intelligence_impacts",
                impact.id,
                {
                    "id": impact.id,
                    "intel_summary_id": summary.id,
                    "impacted_area": impact.impacted_area,
                    "summary": impact.summary,
                    "confidence": impact.confidence.value,
                    "delivered_to_core": delivered_by_impact.get(impact.id, False),
                },
            )
        for event in events:
            self.database.save_document(
                "events",
                event.id,
                {
                    "id": event.id,
                    "event_type": event.event_type.value,
                    "source": event.source,
                    "description": event.description,
                    "location": event.location.label if event.location else None,
                    "confidence": event.confidence.value,
                    "intel_summary_id": event.metadata.get("intel_summary_id"),
                    "intel_impact_id": event.metadata.get("intel_impact_id"),
                    "impacted_area": event.metadata.get("impacted_area"),
                },
            )
