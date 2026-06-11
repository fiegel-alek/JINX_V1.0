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
from jinx.core.schemas import (
    ConflictPacket,
    Event,
    HumanCommandInput,
    MissionContext,
    MissionImpactPacket,
    OperatorReport,
    Recommendation,
)
from jinx.modules.c5isr import C5ISRIntakeResult, C5ISRReportIntake, COPManager, MissionImpactAnalyzer
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
        self.mission_impact_analyzer = MissionImpactAnalyzer()
        self.mission_context: MissionContext | None = None
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

    def set_mission_context(self, mission: MissionContext) -> dict[str, object]:
        self.mission_context = mission
        document = self._mission_document(mission)
        if self.database is not None:
            self.database.save_document("mission_contexts", mission.id, document)
            self.database.save_document("mission_contexts", "active", document)
            self._append_timeline(
                "mission_context",
                "Mission context loaded for C5ISR analysis.",
                {"mission_id": mission.id},
            )
            self._persist_mission_impacts(self._mission_impacts())
        return document

    def validate_cop_track(self, entity_id: str, reviewer_id: str, note: str = "") -> dict[str, object]:
        track = self.cop_manager.validate_track(entity_id, reviewer_id, note)
        if self.database is not None:
            self.database.save_document("cop_states", "latest", self.cop_state_document())
            self._append_timeline(
                "track_validation",
                f"Track {entity_id} marked human_validated.",
                {"entity_id": entity_id, "reviewer_id": reviewer_id, "note": note},
            )
        return {
            "entity_id": track.entity.id,
            "status": track.status,
            "lifecycle": track.metadata.get("lifecycle", track.status),
            "validated_by": reviewer_id,
            "validation_note": note,
        }

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
        report["severity"] = self._severity_for_report(report, state)
        report["assigned_reviewer"] = reviewer_id
        report["escalation_state"] = self._escalation_for_state(state)
        report["review_history"] = history
        self.database.save_document("operator_reports", report_id, report)
        self._append_timeline(
            "report_review",
            f"Report {report_id} marked {state}.",
            {"report_id": report_id, "reviewer_id": reviewer_id, "state": state},
        )
        return report

    def review_center_document(self) -> dict[str, object]:
        if self.database is None:
            return {"items": []}
        reports = self.database.list_documents("operator_reports")
        conflicts = self.database.list_documents("conflicts")
        recommendations = self.database.list_documents("recommendations")
        impacts = self.database.list_documents("mission_impacts")
        items = []
        for report in reports:
            linked_conflicts = [
                conflict["id"]
                for conflict in conflicts
                if report.get("id") in conflict.get("conflicting_items", [])
                or report.get("id") in " ".join(conflict.get("conflicting_items", []))
            ]
            linked_impacts = [
                impact["id"]
                for impact in impacts
                if report.get("id") in impact.get("source_event_ids", [])
                or report.get("reporter_id", "") in impact.get("summary", "")
            ]
            items.append(
                {
                    "id": report["id"],
                    "kind": "operator_report",
                    "summary": report["summary"],
                    "severity": report.get("severity", self._severity_for_report(report, report.get("review_state", "new"))),
                    "confidence": report.get("confidence"),
                    "review_state": report.get("review_state", "new"),
                    "assigned_reviewer": report.get("assigned_reviewer") or report.get("reviewed_by") or "c5isr-manager",
                    "escalation_state": report.get("escalation_state", "none"),
                    "linked_conflicts": linked_conflicts,
                    "linked_recommendations": [item["id"] for item in recommendations[:3]],
                    "linked_mission_impacts": linked_impacts,
                    "needs_operator_clarification": report.get("review_state") == "needs_more_info",
                    "needs_intel_review": any("intel" in impact.get("impacted_area", "") for impact in impacts),
                    "needs_net_review": report.get("report_type") == "communications_check",
                }
            )
        return {"items": items}

    def timeline_document(self) -> dict[str, object]:
        if self.database is None:
            return {"timeline": []}
        timeline = self.database.list_documents("timeline")
        if timeline:
            return {"timeline": timeline}
        events = self.database.list_documents("events")
        return {
            "timeline": [
                {
                    "id": event["id"],
                    "kind": "event",
                    "summary": event.get("description", ""),
                    "timestamp": event.get("timestamp", ""),
                    "related_id": event["id"],
                }
                for event in events
            ]
        }

    @staticmethod
    def layer_config_document() -> dict[str, object]:
        return {
            "layers": [
                {"id": "tracks", "label": "Tracks", "enabled": True},
                {"id": "reports", "label": "Reports", "enabled": True},
                {"id": "conflicts", "label": "Conflicts", "enabled": True},
                {"id": "isr", "label": "ISR feeds", "enabled": True},
                {"id": "advisories", "label": "Advisories", "enabled": True},
                {"id": "mission", "label": "Mission areas/routes", "enabled": True},
                {"id": "stale", "label": "Stale tracks", "enabled": True},
                {"id": "synthetic", "label": "Synthetic/replay labels", "enabled": True},
            ]
        }

    def cop_state_document(self) -> dict[str, object]:
        state = self.cop_manager.state()
        reports = self.database.list_documents("operator_reports") if self.database else ()
        advisories = self.database.list_documents("cop_advisories") if self.database else ()
        return {
            "id": state.id,
            "name": state.name,
            "data_mode": state.data_mode.value,
            "mission_context_id": self.mission_context.id if self.mission_context else None,
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
                    "lifecycle": track.metadata.get("lifecycle", "active"),
                    "history_count": int(track.metadata.get("history_count", "1")),
                    "human_validated": track.metadata.get("human_validated") == "True",
                    "track_history": list(self.cop_manager.track_history(track.entity.id)),
                    "report_count": sum(1 for report in reports if report.get("reporter_id") == track.entity.id),
                    "advisory_count": sum(
                        1
                        for advisory in advisories
                        if track.last_report_id in advisory.get("related_report_ids", [])
                    ),
                    "conflict_count": sum(
                        1
                        for conflict in (self.database.list_documents("conflicts") if self.database else ())
                        if track.last_report_id in conflict.get("conflicting_items", [])
                    ),
                    "stale": track.metadata.get("lifecycle") == "stale",
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
                "severity": self._severity_for_report(
                    {"report_type": report.report_type.value, "summary": report.summary}, "new"
                ),
                "assigned_reviewer": "c5isr-manager",
                "escalation_state": "none",
                "linked_conflicts": [],
                "linked_recommendations": [],
                "linked_mission_impacts": [],
                "needs_operator_clarification": False,
                "needs_intel_review": False,
                "needs_net_review": report.report_type.value == "communications_check",
                "timestamp": report.timestamp.isoformat(),
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
                "mission_impact_tags": intake.event.metadata.get("mission_impact_tags", ""),
                "timestamp": intake.event.timestamp.isoformat(),
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
                "timestamp": intake.advisory.timestamp.isoformat(),
            },
        )
        self._append_timeline(
            "operator_report",
            f"{report.reporter_id} submitted {report.report_type.value}.",
            {"report_id": report.id, "event_id": intake.event.id},
        )
        if intake.event.location is not None:
            self.database.save_document("cop_states", "latest", self.cop_state_document())

    def _run_core_analysis(self) -> object | None:
        if not self._events:
            return None
        result = self.core_reasoning.review_events(tuple(self._events))
        self._persist_core_analysis(result.conflicts, result.recommendations)
        self._persist_mission_impacts(self._mission_impacts())
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
                    "mission_impact_tags": event.metadata.get("mission_impact_tags", ""),
                    "timestamp": event.timestamp.isoformat(),
                },
            )
            self._append_timeline(
                "intel_event",
                f"INTEL impact event generated: {event.event_type.value}.",
                {"event_id": event.id, "intel_summary_id": event.metadata.get("intel_summary_id", "")},
            )

    def _mission_impacts(self) -> tuple[MissionImpactPacket, ...]:
        if self.mission_context is None:
            return ()
        return self.mission_impact_analyzer.analyze(self.mission_context, tuple(self._events))

    def _persist_mission_impacts(self, impacts: tuple[MissionImpactPacket, ...]) -> None:
        if self.database is None:
            return
        for impact in impacts:
            self.database.save_document(
                "mission_impacts",
                impact.id,
                {
                    "id": impact.id,
                    "impacted_area": impact.impacted_area,
                    "summary": impact.summary,
                    "source_event_ids": list(impact.source_event_ids),
                    "affected_tasks": list(impact.affected_tasks),
                    "affected_routes": list(impact.affected_routes),
                    "affected_named_areas": list(impact.affected_named_areas),
                    "confidence": impact.confidence.value,
                    "rationale": impact.rationale,
                    "recommended_review_role": impact.recommended_review_role,
                    "required_human_review": impact.required_human_review,
                    "timestamp": impact.timestamp.isoformat(),
                },
            )
            self._append_timeline(
                "mission_impact",
                impact.summary,
                {"impact_id": impact.id, "impacted_area": impact.impacted_area},
            )

    @staticmethod
    def _mission_document(mission: MissionContext) -> dict[str, object]:
        return {
            "id": mission.id,
            "mission_statement": mission.mission_statement,
            "commander_intent": mission.commander_intent,
            "tasks": [
                {
                    "task_id": task.task_id,
                    "title": task.title,
                    "purpose": task.purpose,
                    "assigned_to": task.assigned_to,
                    "route": task.route,
                    "named_area": task.named_area,
                    "timeline": task.timeline,
                    "constraints": list(task.constraints),
                }
                for task in mission.tasks
            ],
            "named_areas": list(mission.named_areas),
            "routes": list(mission.routes),
            "timeline": list(mission.timeline),
            "constraints": list(mission.constraints),
            "assumptions": list(mission.assumptions),
            "missing_information": list(mission.missing_information),
            "data_mode": mission.data_mode.value,
            "simulation_flag": mission.simulation_flag,
            "timestamp": mission.timestamp.isoformat(),
        }

    def _append_timeline(self, kind: str, summary: str, metadata: dict[str, str]) -> None:
        if self.database is None:
            return
        timestamp = datetime.now(UTC)
        document_id = f"{timestamp.isoformat()}-{kind}"
        self.database.save_document(
            "timeline",
            document_id,
            {
                "id": document_id,
                "kind": kind,
                "summary": summary,
                "timestamp": timestamp.isoformat(),
                "metadata": metadata,
            },
        )

    @staticmethod
    def _severity_for_report(report: dict[str, object], state: str) -> str:
        text = f"{report.get('report_type', '')} {report.get('summary', '')}".lower()
        if state == "needs_more_info":
            return "medium"
        if any(term in text for term in ("medical", "hazard", "loss", "outage", "unavailable")):
            return "high"
        if any(term in text for term in ("delay", "logistics", "weather", "route")):
            return "medium"
        return "low"

    @staticmethod
    def _escalation_for_state(state: str) -> str:
        mapping = {
            "new": "none",
            "under_review": "watch",
            "validated": "resolved",
            "needs_more_info": "clarification",
            "closed": "resolved",
        }
        return mapping[state]
