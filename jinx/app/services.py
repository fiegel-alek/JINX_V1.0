"""High-level application orchestration services."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from jinx.adapters import AdapterGate, AdapterManifest
from jinx.brain.chat import BrainChatEngine, BrainChatQuestion
from jinx.brain.confidence import BrainConfidenceEngine
from jinx.brain.context_builder import BoundedBrainContext, BrainContextBuilder
from jinx.brain.explanation import BrainExplanationEngine
from jinx.brain.knowledge.defaults import build_synthetic_doctrine_repository
from jinx.brain.knowledge.models import DoctrineRecord, DoctrineScope
from jinx.brain.knowledge.repository import DoctrineRepository
from jinx.brain.learner import ConservativeLearner
from jinx.brain.option_generation import BrainOptionGenerator
from jinx.bus import FabricMessage, MessageRouter, RouteResult
from jinx.common.types import ConfidenceScore, DataMode, EventType, SafetyClassification
from jinx.core.audit import AuditLog
from jinx.core.identity.defaults import build_default_access_control
from jinx.core.policy import PolicyEngine
from jinx.core.persistence import SQLiteJINXDatabase
from jinx.core.provenance import ProvenanceRecord
from jinx.core.reasoning import CoreReasoningResult, CoreReasoningWorkflow, CoreRecommendationEngine
from jinx.core.registry import build_default_registry
from jinx.core.schemas import (
    ConflictPacket,
    Event,
    HumanCommandInput,
    Location,
    MissionContext,
    MissionImpactPacket,
    OperatorReport,
    Recommendation,
)
from jinx.modules.c5isr import C5ISRIntakeResult, C5ISRReportIntake, COPManager, MissionImpactAnalyzer
from jinx.modules.integrator import IntegratorParseResult, SyntheticMessageFamilyParser
from jinx.modules.intel import IntelligenceFusionEngine, IntelligenceFusionResult, IntelligenceSummary, ISRFeedSnapshot
from jinx.modules.net import NetworkIssue, NetworkPlan, NetworkValidationRun, NetworkValidator
from jinx.modules.sim import C5ISRScenarioPack, default_c5isr_scenario_packs


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


@dataclass(frozen=True, slots=True)
class NetworkPlanResult:
    validation_run: NetworkValidationRun
    issues: tuple[NetworkIssue, ...]
    issue_routes: tuple[RouteResult, ...]
    core_analysis: object | None = None


@dataclass(frozen=True, slots=True)
class IntegratorMessageResult:
    parse_result: IntegratorParseResult
    routes: tuple[RouteResult, ...]
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
        self.access_control = build_default_access_control()
        self.adapter_gate = AdapterGate()
        self.c5isr_intake = C5ISRReportIntake()
        self.cop_manager = COPManager(name="jinx-phase3-cop")
        self.core_reasoning = CoreReasoningWorkflow(self.router)
        self.brain_repository: DoctrineRepository = build_synthetic_doctrine_repository()
        self.brain_chat = BrainChatEngine(self.brain_repository)
        self.brain_context_builder = BrainContextBuilder()
        self.brain_confidence = BrainConfidenceEngine()
        self.brain_explanations = BrainExplanationEngine()
        self.brain_options = BrainOptionGenerator()
        self.brain_learner = ConservativeLearner()
        self.intel_fusion = IntelligenceFusionEngine()
        self.network_validator = NetworkValidator()
        self.mission_impact_analyzer = MissionImpactAnalyzer()
        self.mission_context: MissionContext | None = None
        self._events: list[Event] = []
        if self.database is not None:
            self._ensure_governance_state()
        self._refresh_brain_systems()

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
        self._refresh_operator_loop("operator_report", {"report_id": report.id, "event_id": intake.event.id})
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

    def submit_network_plan(self, plan: NetworkPlan) -> NetworkPlanResult:
        validation_run, issues = self.network_validator.validate_plan(plan)
        routes: list[RouteResult] = []
        events: list[Event] = []
        for issue in issues:
            routes.append(
                self.router.route(
                    FabricMessage(
                        source_module="jinx-net",
                        destination="jinx-core",
                        payload_schema="network_issue.v1",
                        schema_version="1.0",
                        sensitivity_label="synthetic",
                        license_scope="net",
                        provenance_ref=issue.id,
                        payload={
                            "id": issue.id,
                            "issue_type": issue.issue_type,
                            "summary": issue.summary,
                            "affected_nodes": list(issue.affected_nodes),
                            "confidence": issue.confidence.value,
                            "severity": issue.severity,
                            "recommended_review_role": issue.recommended_review_role,
                        },
                        data_mode=plan.data_mode,
                        confidence=issue.confidence,
                    )
                )
            )
            event = self._event_from_network_issue(issue, plan)
            events.append(event)
            self._events.append(event)

        self._persist_network_plan(plan, validation_run, issues, tuple(routes), tuple(events))
        core_analysis = self._run_core_analysis()
        self._refresh_operator_loop("network_plan", {"plan_id": plan.id, "validation_run_id": validation_run.id})
        return NetworkPlanResult(
            validation_run=validation_run,
            issues=tuple(issues),
            issue_routes=tuple(routes),
            core_analysis=core_analysis,
        )

    def submit_integrator_message(self, parse_result: IntegratorParseResult) -> IntegratorMessageResult:
        routes: list[RouteResult] = []
        for target_module in parse_result.intake.route_targets:
            routes.append(
                self.router.route(
                    FabricMessage(
                        source_module="jinx-integrator",
                        destination=target_module,
                        payload_schema="message_intake.v1",
                        schema_version="1.0",
                        sensitivity_label="synthetic",
                        license_scope="integrator",
                        provenance_ref=parse_result.intake.id,
                        payload=parse_result.normalized_payload,
                        data_mode=parse_result.intake.data_mode,
                        confidence=parse_result.intake.confidence,
                    )
                )
            )

        event = self._event_from_integrator_message(parse_result)
        self._events.append(event)
        self._persist_integrator_message(parse_result, tuple(routes), event)
        core_analysis = self._run_core_analysis()
        self._refresh_operator_loop(
            "integrator_message",
            {"message_id": parse_result.intake.id, "parse_run_id": f"integrator-parse-{parse_result.intake.id}"},
        )
        return IntegratorMessageResult(parse_result=parse_result, routes=tuple(routes), core_analysis=core_analysis)

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
        self._refresh_operator_loop("intel_summary", {"summary_id": summary.id})
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
            self._refresh_operator_loop("isr_feed", {"feed_id": snapshot.id})
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
            self._refresh_operator_loop("mission_context", {"mission_id": mission.id})
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

    def brain_query_document(self, query: str = "", tags: tuple[str, ...] = ()) -> dict[str, object]:
        self._refresh_brain_systems()
        search = self.brain_repository.search(query, tags=frozenset(tags))
        return {
            "query": search.query,
            "matches": [
                {
                    "id": record.id,
                    "title": record.title,
                    "scope": record.scope.value,
                    "summary": record.summary,
                    "source": record.source,
                    "applicability": list(record.applicability),
                    "restrictions": list(record.restrictions),
                    "tags": sorted(record.tags),
                }
                for record in search.matches
            ],
        }

    def ask_brain_chat(
        self,
        text: str,
        user_id: str,
        role: str,
        session_id: str | None = None,
        use_core_reachback: bool = True,
    ) -> dict[str, object]:
        self._refresh_brain_systems()
        question = BrainChatQuestion(text=text, user_id=user_id, role=role, session_id=session_id)
        bounded_context = self._brain_bounded_context() if use_core_reachback else None
        context = dict(bounded_context.context) if bounded_context else {}
        exchange = self.brain_chat.answer(question, context)
        references = tuple(self.brain_repository.get(ref) for ref in exchange.answer.references)
        confidence = self.brain_confidence.assess(references, bounded_context)
        explanation = self.brain_explanations.explain(question, exchange.answer, bounded_context)
        options = self.brain_options.generate(question, exchange.answer)
        learning_proposal = self.brain_learner.propose_from_chat(question, exchange.answer)
        document = {
            "session_id": exchange.answer.session_id,
            "question": {
                "id": question.id,
                "text": question.text,
                "user_id": question.user_id,
                "role": question.role,
                "timestamp": question.timestamp.isoformat(),
            },
            "answer": {
                "id": exchange.answer.id,
                "answer_text": exchange.answer.answer_text,
                "confidence_band": exchange.answer.confidence_band,
                "confidence_value": exchange.answer.confidence_value,
                "references": list(exchange.answer.references),
                "assumptions": list(exchange.answer.assumptions),
                "uncertainty": exchange.answer.uncertainty,
                "allowed_next_steps": list(exchange.answer.allowed_next_steps),
                "disallowed_actions": list(exchange.answer.disallowed_actions),
                "core_reachback_used": exchange.answer.core_reachback_used,
                "human_review_required": exchange.answer.human_review_required,
                "timestamp": exchange.answer.timestamp.isoformat(),
            },
        }
        if self.database is not None:
            if bounded_context is not None:
                self.database.save_document(
                    "brain_contexts",
                    bounded_context.id,
                    self._brain_context_document(bounded_context),
                )
            self.database.save_document(
                "brain_confidence",
                exchange.answer.id,
                {
                    "id": exchange.answer.id,
                    "question_id": question.id,
                    "answer_id": exchange.answer.id,
                    "value": confidence.value,
                    "scale": confidence.scale,
                    "rationale": confidence.rationale,
                    "source_quality": confidence.source_quality,
                    "recency_factor": confidence.recency_factor,
                    "corroboration_factor": confidence.corroboration_factor,
                    "contradiction_factor": confidence.contradiction_factor,
                    "completeness_factor": confidence.completeness_factor,
                },
            )
            self.database.save_document(
                "brain_explanations",
                explanation.id,
                {
                    "id": explanation.id,
                    "question_id": explanation.question_id,
                    "answer_id": explanation.answer_id,
                    "what_was_detected": explanation.what_was_detected,
                    "why_it_matters": explanation.why_it_matters,
                    "references": list(explanation.references),
                    "assumptions": list(explanation.assumptions),
                    "uncertainty": list(explanation.uncertainty),
                    "redactions": list(explanation.redactions),
                    "recommended_review_role": explanation.recommended_review_role,
                    "timestamp": explanation.timestamp.isoformat(),
                },
            )
            for option in options:
                self.database.save_document(
                    "brain_options",
                    option.id,
                    {
                        "id": option.id,
                        "answer_id": exchange.answer.id,
                        "description": option.description,
                        "rationale": option.rationale,
                        "assumptions": list(option.assumptions),
                        "risks": list(option.risks),
                        "tradeoffs": list(option.tradeoffs),
                        "confidence_band": option.confidence_band,
                        "required_human_approval": option.required_human_approval,
                        "affected_modules": list(option.affected_modules),
                        "disallowed_actions": list(option.disallowed_actions),
                        "timestamp": option.timestamp.isoformat(),
                    },
                )
            self.database.save_document(
                "learning_proposals",
                learning_proposal.id,
                {
                    "id": learning_proposal.id,
                    "source_question_id": learning_proposal.source_question_id,
                    "source_answer_id": learning_proposal.source_answer_id,
                    "proposal_type": learning_proposal.proposal_type,
                    "summary": learning_proposal.summary,
                    "evidence_refs": list(learning_proposal.evidence_refs),
                    "review_status": learning_proposal.review_status,
                    "required_reviewer_role": learning_proposal.required_reviewer_role,
                    "timestamp": learning_proposal.timestamp.isoformat(),
                },
            )
            self._save_evidence_pack(
                source_kind="brain_answer",
                source_id=exchange.answer.id,
                source_module="jinx-brain",
                package_scope="full",
                title=f"BRAIN answer for {question.role}",
                summary=exchange.answer.answer_text,
                confidence_value=exchange.answer.confidence_value,
                recommended_review_role=explanation.recommended_review_role,
                related_ids=(question.id, *exchange.answer.references),
                provenance_refs=tuple(exchange.answer.references),
                assumptions=tuple(exchange.answer.assumptions),
                uncertainty=(exchange.answer.uncertainty,),
                redactions=tuple(explanation.redactions),
                brain_references=tuple(exchange.answer.references),
                allowed_actions=tuple(exchange.answer.allowed_next_steps),
                disallowed_actions=tuple(exchange.answer.disallowed_actions),
                tags=("brain", "chat", question.role),
            )
            self._save_evidence_pack(
                source_kind="learning_proposal",
                source_id=learning_proposal.id,
                source_module="jinx-brain",
                package_scope="full",
                title="BRAIN learning proposal",
                summary=learning_proposal.summary,
                confidence_value=confidence.value,
                recommended_review_role=learning_proposal.required_reviewer_role.replace("_", " "),
                related_ids=(question.id, exchange.answer.id, *learning_proposal.evidence_refs),
                provenance_refs=tuple(learning_proposal.evidence_refs),
                assumptions=("Learning proposals require human approval before doctrine promotion.",),
                uncertainty=("Proposal has not been promoted into doctrine.",),
                brain_references=tuple(exchange.answer.references),
                tags=("brain", "learning", "proposal"),
            )
            self.database.save_document("brain_chat_sessions", exchange.answer.session_id, {"id": exchange.answer.session_id})
            self.database.save_document("brain_chat_messages", exchange.answer.id, document)
            self._append_timeline(
                "brain_chat",
                "Brain chat answered an advisory question.",
                {"session_id": exchange.answer.session_id, "answer_id": exchange.answer.id},
            )
            self._refresh_operator_loop("brain_chat", {"answer_id": exchange.answer.id})
        return document

    def brain_chat_sessions_document(self) -> dict[str, object]:
        return {"sessions": self.database.list_documents("brain_chat_sessions") if self.database else []}

    def brain_chat_messages_document(self) -> dict[str, object]:
        return {"messages": self.database.list_documents("brain_chat_messages") if self.database else []}

    def brain_contexts_document(self) -> dict[str, object]:
        return {"contexts": self.database.list_documents("brain_contexts") if self.database else []}

    def brain_explanations_document(self) -> dict[str, object]:
        return {"brain_explanations": self.database.list_documents("brain_explanations") if self.database else []}

    def brain_options_document(self) -> dict[str, object]:
        return {"brain_options": self.database.list_documents("brain_options") if self.database else []}

    def learning_proposals_document(self) -> dict[str, object]:
        return {"learning_proposals": self.database.list_documents("learning_proposals") if self.database else []}

    def doctrine_library_document(
        self,
        scope: str = "",
        tags: tuple[str, ...] = (),
    ) -> dict[str, object]:
        self._refresh_brain_systems()
        scope_filter = DoctrineScope(scope) if scope else None
        tag_filter = frozenset(item for item in tags if item)
        records = []
        for record in self.brain_repository.all():
            if scope_filter is not None and record.scope != scope_filter:
                continue
            if tag_filter and not tag_filter.issubset(record.tags):
                continue
            records.append(
                {
                    "id": record.id,
                    "title": record.title,
                    "scope": record.scope.value,
                    "summary": record.summary,
                    "source": record.source,
                    "applicability": list(record.applicability),
                    "restrictions": list(record.restrictions),
                    "tags": sorted(record.tags),
                }
            )
        scope_counts: dict[str, int] = {}
        for record in records:
            scope_counts[record["scope"]] = scope_counts.get(record["scope"], 0) + 1
        return {
            "doctrine_library": {
                "records": records,
                "summary": {
                    "total": len(records),
                    "scope_counts": scope_counts,
                },
            }
        }

    def register_doctrine_record(
        self,
        title: str,
        scope: str,
        summary: str,
        source: str,
        applicability: tuple[str, ...],
        restrictions: tuple[str, ...],
        tags: tuple[str, ...],
    ) -> dict[str, object]:
        if self.database is None:
            raise ValueError("database is required for doctrine registration")
        record = DoctrineRecord(
            title=title,
            scope=DoctrineScope(scope),
            summary=summary,
            source=source,
            applicability=applicability,
            restrictions=restrictions,
            tags=frozenset(tags),
        )
        document = {
            "id": record.id,
            "title": record.title,
            "scope": record.scope.value,
            "summary": record.summary,
            "source": record.source,
            "applicability": list(record.applicability),
            "restrictions": list(record.restrictions),
            "tags": sorted(record.tags),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.database.save_document("doctrine_library", record.id, document)
        self._append_timeline(
            "doctrine_record",
            f"Doctrine record {record.title} registered for BRAIN use.",
            {"record_id": record.id, "scope": record.scope.value},
        )
        self._refresh_brain_systems()
        return {"doctrine_record": document}

    def promote_learning_proposal(
        self,
        proposal_id: str,
        title: str = "",
        scope: str = DoctrineScope.LESSON_LEARNED.value,
        source: str = "",
        applicability: tuple[str, ...] = (),
        restrictions: tuple[str, ...] = (),
        tags: tuple[str, ...] = (),
        reviewer_id: str = "",
        note: str = "",
    ) -> dict[str, object]:
        if self.database is None:
            raise ValueError("database is required for learning promotion")
        proposal = self.database.get_document("learning_proposals", proposal_id)
        created = self.register_doctrine_record(
            title=title or f"Promoted lesson from {proposal_id}",
            scope=scope,
            summary=proposal.get("summary", "Approved learning proposal."),
            source=source or f"learning-proposal:{proposal_id}",
            applicability=applicability or ("after_action_review", "brain_reference", "human_review"),
            restrictions=restrictions
            or (
                "Synthetic or explicitly authorized advisory reference only.",
                "Does not authorize operational action.",
            ),
            tags=tags or ("lesson", "review", "advisory"),
        )
        proposal["review_status"] = "approved"
        proposal["promoted_doctrine_id"] = created["doctrine_record"]["id"]
        proposal["reviewed_by"] = reviewer_id or "systemadministrator"
        proposal["review_note"] = note
        proposal["reviewed_at"] = datetime.now(UTC).isoformat()
        self.database.save_document("learning_proposals", proposal_id, proposal)
        self._persist_memory_record(
            compartment="brain.shared",
            package_scope="full",
            title=created["doctrine_record"]["title"],
            summary=f"Learning proposal promoted into doctrine library. {proposal.get('summary', '')}",
            tags=("lesson", "promoted", "brain"),
            source_kind="learning_proposal",
            source_id=proposal_id,
            created_by=reviewer_id or "systemadministrator",
            provenance_refs=tuple(proposal.get("evidence_refs", ())),
            review_state="approved",
        )
        return {
            "learning_proposal": proposal,
            "doctrine_record": created["doctrine_record"],
        }

    def brain_checklists_document(self) -> dict[str, object]:
        self._refresh_brain_systems()
        records = [
            record
            for record in self.brain_repository.all()
            if record.scope == DoctrineScope.REVIEW_CHECKLIST
        ]
        return {
            "checklists": [
                {
                    "id": record.id,
                    "title": record.title,
                    "summary": record.summary,
                    "source": record.source,
                    "applicability": list(record.applicability),
                    "restrictions": list(record.restrictions),
                    "tags": sorted(record.tags),
                }
                for record in records
            ]
        }

    def evidence_packs_document(self, package_scope: str = "", source_kind: str = "") -> dict[str, object]:
        if self.database is None:
            return {"evidence_packs": [], "summary": {"total": 0, "by_kind": {}}}
        records = list(self.database.list_documents("evidence_packs"))
        if package_scope:
            records = [record for record in records if record.get("package_scope") in {package_scope, "full"}]
        if source_kind:
            records = [record for record in records if record.get("source_kind") == source_kind]
        by_kind: dict[str, int] = {}
        for record in records:
            kind = str(record.get("source_kind", "unknown"))
            by_kind[kind] = by_kind.get(kind, 0) + 1
        return {"evidence_packs": records, "summary": {"total": len(records), "by_kind": by_kind}}

    def review_tasks_document(
        self,
        package_scope: str = "",
        state: str = "",
        assigned_role: str = "",
        assigned_reviewer: str = "",
        escalation_state: str = "",
        source_kind: str = "",
    ) -> dict[str, object]:
        self._sync_review_tasks()
        if self.database is None:
            return {"review_tasks": [], "summary": {"total": 0, "open": 0}}
        records = list(self.database.list_documents("review_tasks"))
        if package_scope:
            records = [record for record in records if record.get("package_scope") in {package_scope, "full"}]
        if state:
            records = [record for record in records if record.get("state") == state]
        if assigned_role:
            records = [record for record in records if record.get("assigned_role") == assigned_role]
        if assigned_reviewer:
            records = [record for record in records if record.get("assigned_reviewer") == assigned_reviewer]
        if escalation_state:
            records = [record for record in records if record.get("escalation_state") == escalation_state]
        if source_kind:
            records = [record for record in records if record.get("source_kind") == source_kind]
        open_count = sum(1 for record in records if record.get("state") not in {"validated", "closed", "rejected"})
        escalated_count = sum(
            1 for record in records if str(record.get("escalation_state", "none")) in {"watch", "elevated", "critical"}
        )
        by_package: dict[str, int] = {}
        by_state: dict[str, int] = {}
        for record in records:
            package = str(record.get("package_scope", "full"))
            by_package[package] = by_package.get(package, 0) + 1
            record_state = str(record.get("state", "new"))
            by_state[record_state] = by_state.get(record_state, 0) + 1
        return {
            "review_tasks": records,
            "summary": {
                "total": len(records),
                "open": open_count,
                "escalated": escalated_count,
                "by_package": by_package,
                "by_state": by_state,
            },
        }

    def update_review_task(
        self,
        task_id: str,
        state: str,
        reviewer_id: str,
        note: str = "",
        remember: bool = False,
        assigned_role: str = "",
        assigned_reviewer: str = "",
        escalation_state: str = "",
        priority: str = "",
        due_label: str = "",
    ) -> dict[str, object]:
        self._sync_review_tasks()
        if self.database is None:
            raise ValueError("database is required for review workflow")
        allowed_states = {"new", "acknowledged", "validated", "rejected", "needs_more_info", "closed"}
        if state and state not in allowed_states:
            raise ValueError(f"invalid review task state: {state}")
        task = self.database.get_document("review_tasks", task_id)
        history = list(task.get("history", []))
        next_state = state or str(task.get("state", "new"))
        assignment_changes: dict[str, str] = {}
        if assigned_role:
            assignment_changes["assigned_role"] = assigned_role
        if assigned_reviewer:
            assignment_changes["assigned_reviewer"] = assigned_reviewer
        elif assigned_role:
            assignment_changes["assigned_reviewer"] = self._default_reviewer_for_role(assigned_role)
        if escalation_state:
            assignment_changes["escalation_state"] = escalation_state
        if priority:
            assignment_changes["priority"] = priority
        if due_label:
            assignment_changes["due_label"] = due_label
        history.append(
            {
                "state": next_state,
                "reviewer_id": reviewer_id,
                "note": note,
                "assignment_changes": assignment_changes,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        task["state"] = next_state
        task["reviewed_by"] = reviewer_id
        task["last_note"] = note
        task["history"] = history
        task["updated_at"] = datetime.now(UTC).isoformat()
        for key, value in assignment_changes.items():
            task[key] = value
        if next_state == "acknowledged":
            task["acknowledged_by"] = reviewer_id
        self.database.save_document("review_tasks", task_id, task)
        self._apply_review_state_to_source(task, next_state, reviewer_id, note)
        if remember or next_state in {"validated", "rejected"}:
            self._persist_memory_record(
                compartment=self._memory_compartment_for_package(str(task.get("package_scope", "full"))),
                package_scope=str(task.get("package_scope", "full")),
                title=str(task.get("title", task_id)),
                summary=note or str(task.get("summary", "")),
                tags=(str(task.get("source_kind", "review")), "review"),
                source_kind="review_task",
                source_id=task_id,
                created_by=reviewer_id,
                provenance_refs=tuple(task.get("provenance_refs", ())),
                review_state=next_state,
            )
        self._append_timeline(
            "review_task",
            f"Review task {task_id} marked {next_state}.",
            {
                "task_id": task_id,
                "reviewer_id": reviewer_id,
                "state": next_state,
                "assigned_role": task.get("assigned_role", ""),
                "assigned_reviewer": task.get("assigned_reviewer", ""),
                "escalation_state": task.get("escalation_state", ""),
            },
        )
        return {"review_task": task}

    def memory_compartments_document(self, package_scope: str = "") -> dict[str, object]:
        if self.database is None:
            return {"memory": {"compartments": [], "records": []}}
        records = list(self.database.list_documents("compartment_memories"))
        if package_scope:
            records = [record for record in records if record.get("package_scope") in {package_scope, "full"}]
        compartment_counts: dict[str, int] = {}
        for record in records:
            compartment = str(record.get("compartment", "unknown"))
            compartment_counts[compartment] = compartment_counts.get(compartment, 0) + 1
        compartments = [
            {"name": name, "count": count}
            for name, count in sorted(compartment_counts.items(), key=lambda item: item[0])
        ]
        return {"memory": {"compartments": compartments, "records": records}}

    def write_memory_record(
        self,
        compartment: str,
        package_scope: str,
        title: str,
        summary: str,
        tags: tuple[str, ...],
        source_kind: str,
        source_id: str,
        created_by: str,
        provenance_refs: tuple[str, ...] = (),
        review_state: str = "captured",
    ) -> dict[str, object]:
        document = self._persist_memory_record(
            compartment=compartment,
            package_scope=package_scope,
            title=title,
            summary=summary,
            tags=tags,
            source_kind=source_kind,
            source_id=source_id,
            created_by=created_by,
            provenance_refs=provenance_refs,
            review_state=review_state,
        )
        return {"memory_record": document}

    def recall_document(
        self,
        query: str,
        package_scope: str = "",
        kind: str = "",
        state: str = "",
        assigned_role: str = "",
        limit: int = 40,
    ) -> dict[str, object]:
        query_text = query.strip().lower()
        results: list[dict[str, object]] = []
        allowed_kinds = {kind} if kind else {"evidence_pack", "review_task", "memory_record", "doctrine_record"}
        if self.database is not None:
            if "evidence_pack" in allowed_kinds:
                for record in self.database.list_documents("evidence_packs"):
                    if package_scope and record.get("package_scope") not in {package_scope, "full"}:
                        continue
                    if self._matches_recall_query(query_text, record, ("title", "summary", "source_kind", "recommended_review_role")):
                        results.append(
                            {
                                "kind": "evidence_pack",
                                "id": record["id"],
                                "title": record.get("title", record["id"]),
                                "summary": record.get("summary", ""),
                                "package_scope": record.get("package_scope", "full"),
                                "source_kind": record.get("source_kind", ""),
                                "matched_on": "evidence",
                            }
                        )
            if "review_task" in allowed_kinds:
                for record in self.database.list_documents("review_tasks"):
                    if package_scope and record.get("package_scope") not in {package_scope, "full"}:
                        continue
                    if state and record.get("state") != state:
                        continue
                    if assigned_role and record.get("assigned_role") != assigned_role:
                        continue
                    if self._matches_recall_query(query_text, record, ("title", "summary", "state", "assigned_role", "assigned_reviewer", "escalation_state")):
                        results.append(
                            {
                                "kind": "review_task",
                                "id": record["id"],
                                "title": record.get("title", record["id"]),
                                "summary": record.get("summary", ""),
                                "package_scope": record.get("package_scope", "full"),
                                "source_kind": record.get("source_kind", ""),
                                "matched_on": "review",
                                "state": record.get("state", "new"),
                            }
                        )
            if "memory_record" in allowed_kinds:
                for record in self.database.list_documents("compartment_memories"):
                    if package_scope and record.get("package_scope") not in {package_scope, "full"}:
                        continue
                    if self._matches_recall_query(query_text, record, ("title", "summary", "compartment")):
                        results.append(
                            {
                                "kind": "memory_record",
                                "id": record["id"],
                                "title": record.get("title", record["id"]),
                                "summary": record.get("summary", ""),
                                "package_scope": record.get("package_scope", "full"),
                                "source_kind": record.get("source_kind", ""),
                                "matched_on": "memory",
                            }
                        )
        if "doctrine_record" in allowed_kinds:
            for record in self.doctrine_library_document()["doctrine_library"]["records"]:
                if self._matches_recall_query(query_text, record, ("title", "summary", "scope", "source")):
                    results.append(
                        {
                            "kind": "doctrine_record",
                            "id": record["id"],
                            "title": record["title"],
                            "summary": record["summary"],
                            "package_scope": "full",
                            "source_kind": record.get("scope", ""),
                            "matched_on": "doctrine",
                        }
                    )
        return {
            "recall": {
                "query": query,
                "filters": {
                    "package_scope": package_scope,
                    "kind": kind,
                    "state": state,
                    "assigned_role": assigned_role,
                    "limit": limit,
                },
                "results": results[:limit],
                "count": len(results),
            }
        }

    def adapter_runs_document(self) -> dict[str, object]:
        return {"adapter_runs": self.database.list_documents("adapter_runs") if self.database else []}

    def execute_adapter(
        self,
        adapter_id: str,
        initiated_by: str,
        summary: str = "",
    ) -> dict[str, object]:
        self._ensure_governance_state()
        if self.database is None:
            raise ValueError("database is required for adapter execution")
        adapter = self._evaluated_adapter_document(self._adapter_document(adapter_id))
        run_id = f"adapter-run-{uuid4().hex[:12]}"
        status = "blocked"
        produced: list[str] = []
        notes = summary or str(adapter.get("notes", ""))
        if adapter.get("enabled") and adapter.get("gate_allowed") and adapter.get("policy_allowed"):
            handler = self._api_handler()
            status = "completed"
            if adapter_id == "adapter-weather-open":
                response = handler.submit_intelligence_summary(
                    {
                        "source_category": "open_weather_stub",
                        "summary": "Open weather stub indicates synthetic route visibility and weather constraints for human review.",
                        "reliability": "0.66",
                        "related_locations": "Route Alpha,Area Alpha",
                    }
                )
                produced.extend([response["summary_id"], *response["impact_ids"]])
                notes = "Adapter run created a synthetic weather-context INTEL summary."
            elif adapter_id == "adapter-intel-summary":
                response = handler.submit_intelligence_summary(
                    {
                        "source_category": "synthetic_adapter_summary",
                        "summary": "Synthetic adapter summary created an analyst review packet for doctrine and memory testing.",
                        "reliability": "0.7",
                        "related_locations": "Area Alpha",
                    }
                )
                produced.extend([response["summary_id"], *response["impact_ids"]])
                notes = "Adapter run created a synthetic intelligence summary."
            elif adapter_id == "adapter-network-plan":
                response = handler.submit_network_plan(
                    {
                        "name": "Adapter Generated Relay Plan",
                        "node_ids": "node-alpha,node-bravo",
                        "timeslots": "slot-01:node-alpha,slot-01:node-bravo",
                        "los_links": "node-alpha>node-bravo",
                        "los_status": "degraded",
                        "los_rationale": "Synthetic adapter path generated this plan for human review.",
                    }
                )
                produced.extend([response["plan_id"], response["validation_run_id"], *response["issue_ids"]])
                notes = "Adapter run created a synthetic network plan and validation run."
            elif adapter_id == "adapter-geospatial-mock":
                response = self.set_mission_context(
                    MissionContext(
                        mission_statement="Synthetic geospatial adapter refreshed route and named-area context.",
                        commander_intent="Preserve advisory traceability.",
                        tasks=(
                            MissionTask(
                                task_id="task-geo-alpha",
                                title="Synthetic geospatial overlay refresh",
                                purpose="Refresh named-area context for review.",
                                assigned_to="c5isr-manager-alpha",
                                route="Route Alpha",
                                named_area="Area Alpha",
                                timeline="T+00 to T+45",
                                constraints=("Synthetic data only.", "Human review required."),
                            ),
                        ),
                        named_areas=("Area Alpha",),
                        routes=("Route Alpha",),
                        timeline=("T+00 to T+45",),
                        constraints=("Synthetic overlay only.",),
                        assumptions=("Geospatial adapter execution is mock only.",),
                        missing_information=("Human map validation.",),
                        data_mode=DataMode.MOCK,
                        provenance=self._synthetic_provenance("jinx-adapter.geospatial"),
                    )
                )
                produced.append(str(response["id"]))
                notes = "Adapter run refreshed synthetic mission/geospatial context."
            elif adapter_id == "adapter-message-integrator":
                response = handler.submit_integrator_message(
                    {
                        "message_family": "j-series",
                        "raw_text": (
                            "message_type: j3.5 track update\n"
                            "originator: unit-alpha\n"
                            "recipient: review-cell\n"
                            "summary: Synthetic track and communications status update for replay.\n"
                            "transport: fabric-shadow\n"
                            "precedence: routine\n"
                            "location: grid-alpha\n"
                            "tags: communications,track\n"
                        ),
                    }
                )
                produced.extend([response["message_id"], response["parse_run_id"]])
                notes = "Adapter run created a synthetic JINX-Integrator intake record."
            elif adapter.get("data_mode") == DataMode.LIVE_CONTROLLED_ADAPTER.value:
                status = "stub_ready"
                notes = (
                    "Controlled live adapter path was exercised as a governed stub only. "
                    "No external system connection or tasking occurred."
                )
            else:
                notes = "Adapter execution completed with a governed synthetic no-op."
        document = {
            "id": run_id,
            "adapter_id": adapter_id,
            "adapter_name": adapter.get("name"),
            "target_module": adapter.get("target_module"),
            "status": status,
            "initiated_by": initiated_by,
            "data_mode": adapter.get("data_mode"),
            "policy_allowed": adapter.get("policy_allowed"),
            "gate_allowed": adapter.get("gate_allowed"),
            "explicitly_authorized": adapter.get("explicitly_authorized"),
            "produced_records": produced,
            "summary": notes,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self.database.save_document("adapter_runs", run_id, document)
        self._save_evidence_pack(
            source_kind="adapter_run",
            source_id=run_id,
            source_module=str(adapter.get("target_module", "jinx-core")),
            package_scope="full",
            title=f"Adapter run {adapter.get('name', adapter_id)}",
            summary=notes,
            confidence_value=0.61 if status == "completed" else 0.42,
            recommended_review_role="system administrator",
            related_ids=tuple(produced),
            provenance_refs=(adapter_id,),
            assumptions=("Adapter execution remains synthetic or controlled-stub only.",),
            uncertainty=("No live external integration was performed.",),
            tags=("adapter", "execution", status),
        )
        self._append_timeline(
            "adapter_run",
            f"Adapter {adapter.get('name', adapter_id)} executed with status {status}.",
            {"adapter_run_id": run_id, "adapter_id": adapter_id},
        )
        return {"adapter_run": document}

    def audit_replay_document(self) -> dict[str, object]:
        if self.database is not None and self.database.count("audit_replay_runs") > 0:
            return {"audit_replay": self.database.list_documents("audit_replay_runs")[-1]}
        return {"audit_replay": self._build_audit_replay_document()}

    def create_audit_replay(
        self,
        focus_id: str = "",
        limit: int = 12,
        package_scope: str = "",
        source_kind: str = "",
        query: str = "",
    ) -> dict[str, object]:
        if self.database is None:
            raise ValueError("database is required for audit replay")
        replay = self._build_audit_replay_document(
            focus_id=focus_id,
            limit=limit,
            package_scope=package_scope,
            source_kind=source_kind,
            query=query,
        )
        self.database.save_document("audit_replay_runs", replay["id"], replay)
        self._append_timeline(
            "audit_replay",
            "After-action audit replay generated for human review.",
            {
                "audit_replay_id": replay["id"],
                "focus_id": focus_id,
                "package_scope": package_scope,
                "source_kind": source_kind,
                "query": query,
            },
        )
        return {"audit_replay": replay}

    def network_plans_document(self) -> dict[str, object]:
        return {"network_plans": self.database.list_documents("network_plans") if self.database else []}

    def network_issues_document(self) -> dict[str, object]:
        return {"network_issues": self.database.list_documents("network_issues") if self.database else []}

    def network_validation_runs_document(self) -> dict[str, object]:
        return {"network_validation_runs": self.database.list_documents("network_validation_runs") if self.database else []}

    def network_advisories_document(self) -> dict[str, object]:
        return {"network_advisories": self.database.list_documents("network_advisories") if self.database else []}

    def integrator_messages_document(self) -> dict[str, object]:
        return {"integrator_messages": self.database.list_documents("integrator_messages") if self.database else []}

    def integrator_parser_runs_document(self) -> dict[str, object]:
        return {"integrator_parser_runs": self.database.list_documents("integrator_parser_runs") if self.database else []}

    def integrator_routes_document(self) -> dict[str, object]:
        return {"integrator_routes": self.database.list_documents("integrator_routes") if self.database else []}

    def integrator_profiles_document(self) -> dict[str, object]:
        return SyntheticMessageFamilyParser.profiles_document()

    def intelligence_summaries_document(self) -> dict[str, object]:
        return {
            "intelligence_summaries": self.database.list_documents("intelligence_summaries") if self.database else []
        }

    def intelligence_impacts_document(self) -> dict[str, object]:
        return {"intelligence_impacts": self.database.list_documents("intelligence_impacts") if self.database else []}

    def intelligence_correlations_document(self) -> dict[str, object]:
        return {"intel_correlations": self.database.list_documents("intel_correlations") if self.database else []}

    def intelligence_module_notices_document(self) -> dict[str, object]:
        return {
            "intel_module_notices": self.database.list_documents("intel_module_notices") if self.database else []
        }

    def isr_feeds_document(self) -> dict[str, object]:
        return {"isr_feeds": self.database.list_documents("isr_feeds") if self.database else []}

    def fabric_monitor_document(self) -> dict[str, object]:
        self._sync_fabric_ledger()
        if self.database is None:
            messages = [record.to_document() for record in self.router.route_records()]
            dead_letters = [record for record in messages if record["status"] == "denied"]
        else:
            messages = list(self.database.list_documents("fabric_messages"))
            dead_letters = list(self.database.list_documents("fabric_dead_letters"))
        counts = {
            "delivered": sum(1 for message in messages if message.get("status") == "delivered"),
            "redacted": sum(1 for message in messages if message.get("status") == "redacted"),
            "denied": sum(1 for message in messages if message.get("status") == "denied"),
            "dead_letters": len(dead_letters),
        }
        topics = sorted({str(message.get("topic", "")) for message in messages if message.get("topic")})
        return {
            "fabric": {
                "status": "monitoring",
                "mode": "policy_enforced_simulation",
                "authority": "advisory_only_human_in_the_loop",
                "messages": messages,
                "dead_letters": dead_letters,
                "counts": counts,
                "topics": topics,
            }
        }

    def analysis_runs_document(self) -> dict[str, object]:
        return {"analysis_runs": self.database.list_documents("analysis_runs") if self.database else []}

    def explanations_document(self) -> dict[str, object]:
        return {"explanations": self.database.list_documents("explanations") if self.database else []}

    def audit_document(self) -> dict[str, object]:
        self._sync_audit_ledger()
        if self.database is not None:
            return {"audit_records": self.database.list_documents("audit_records")}
        return {
            "audit_records": [
                {
                    "id": record.id,
                    "event_type": record.event_type.value,
                    "actor": record.actor,
                    "summary": record.summary,
                    "metadata": dict(record.metadata),
                    "timestamp": record.timestamp.isoformat(),
                }
                for record in self.audit_log.records()
            ]
        }

    def policy_decisions_document(self) -> dict[str, object]:
        self._sync_audit_ledger()
        if self.database is None:
            return {"policy_decisions": []}
        return {"policy_decisions": self.database.list_documents("policy_decisions")}

    def provenance_document(self) -> dict[str, object]:
        self._sync_provenance_ledger()
        if self.database is not None:
            return {"provenance": self.database.list_documents("provenance_records")}
        provenance = []
        for event in self._events:
            provenance.append(
                {
                    "id": f"prov-{event.id}",
                    "source": event.provenance.source,
                    "processed_by_module": event.provenance.processed_by_module,
                    "transformations": list(event.provenance.transformations),
                    "confidence": event.provenance.confidence.value,
                    "time_received": event.provenance.time_received.isoformat(),
                    "event_id": event.id,
                }
            )
        return {"provenance": provenance}

    def core_context_document(self) -> dict[str, object]:
        if self.database is None:
            return {"core_context": {}}
        raw = self._bounded_core_reachback()
        context = self.brain_context_builder.build(
            raw,
            allowed_modules=self._licensed_module_names(),
            source="jinx-core.context-builder",
        )
        document = self._brain_context_document(context)
        self.database.save_document("core_contexts", context.id, document)
        return {"core_context": document}

    def module_boundary_document(self) -> dict[str, object]:
        registry = build_default_registry()
        modules = registry.licensed_modules()
        delivered = self.router.delivered_messages()
        dead_letters = self.router.dead_letters()
        route_records = self.router.route_records()
        return {
            "modules": [
                {
                    "name": module.name,
                    "license_scope": module.license_scope,
                    "allowed_inputs": sorted(module.allowed_inputs),
                    "allowed_outputs": sorted(module.allowed_outputs),
                    "dependencies": sorted(module.dependencies),
                    "supports_simulation": module.supports_simulation,
                }
                for module in modules
            ],
            "routes": [
                {
                    "id": message.id,
                    "source_module": message.source_module,
                    "destination": message.destination,
                    "topic": message.topic,
                    "payload_schema": message.payload_schema,
                    "license_scope": message.license_scope,
                    "status": next(
                        (record.status for record in route_records if record.message.id == message.id),
                        "delivered",
                    ),
                }
                for message in delivered
            ],
            "dead_letters": [
                {
                    "id": message.id,
                    "source_module": message.source_module,
                    "destination": message.destination,
                    "topic": message.topic,
                    "payload_schema": message.payload_schema,
                    "license_scope": message.license_scope,
                    "status": "denied",
                }
                for message in dead_letters
            ],
        }

    def core_ops_console_document(self) -> dict[str, object]:
        self._sync_fabric_ledger()
        if self.database is None:
            counts = {}
        else:
            counts = {
                "operator_reports": self.database.count("operator_reports"),
                "events": self.database.count("events"),
                "conflicts": self.database.count("conflicts"),
                "recommendations": self.database.count("recommendations"),
                "mission_impacts": self.database.count("mission_impacts"),
                "isr_feeds": self.database.count("isr_feeds"),
                "integrator_messages": self.database.count("integrator_messages"),
                "brain_chat_messages": self.database.count("brain_chat_messages"),
                "brain_options": self.database.count("brain_options"),
                "learning_proposals": self.database.count("learning_proposals"),
                "policy_decisions": self.database.count("policy_decisions"),
                "network_plans": self.database.count("network_plans"),
                "network_issues": self.database.count("network_issues"),
                "intelligence_summaries": self.database.count("intelligence_summaries"),
                "intelligence_impacts": self.database.count("intelligence_impacts"),
                "intel_correlations": self.database.count("intel_correlations"),
                "simulation_runs": self.database.count("simulation_runs"),
                "fabric_messages": self.database.count("fabric_messages"),
                "fabric_dead_letters": self.database.count("fabric_dead_letters"),
            }
        boundary = self.module_boundary_document()
        fabric = self.fabric_monitor_document()["fabric"]
        return {
            "mode": "simulation_first",
            "live_adapters": "disabled",
            "authority": "advisory_only_human_in_the_loop",
            "health": {
                "core": "online",
                "brain": "online",
                "c5isr": "online",
                "sim": "online",
                "bus": "online",
            },
            "counts": counts,
            "licensed_modules": [module["name"] for module in boundary["modules"]],
            "delivered_routes": len(boundary["routes"]),
            "denied_routes": len(boundary["dead_letters"]),
            "fabric_counts": fabric["counts"],
            "audit_records": len(self.audit_document()["audit_records"]),
            "provenance_records": len(self.provenance_document()["provenance"]),
            "active_operator_loop": self.operator_loop_document()["operator_loop"],
            "active_core_context": self.core_context_document()["core_context"],
            "guardrails": [
                "JINX-Core produces advisory analysis only.",
                "Human input is required for command decisions.",
                "Synthetic, mock, open, or explicitly authorized data only.",
                "Real-world adapters remain controlled plugins.",
            ],
        }

    def operator_loop_document(self) -> dict[str, object]:
        if self.database is None:
            return {"operator_loop": self._build_operator_loop_packet("memory_only", {})}
        try:
            packet = self.database.get_document("operator_loop_packets", "active")
        except KeyError:
            packet = self._refresh_operator_loop("bootstrap", {})
        return {"operator_loop": packet}

    def operator_workspace_document(
        self,
        reporter_id: str,
        device_id: str = "",
    ) -> dict[str, object]:
        mission = {
            "id": None,
            "mission_statement": "No local mission context loaded.",
            "routes": [],
            "named_areas": [],
            "timeline": [],
        }
        if self.database is not None:
            try:
                mission = self.database.get_document("mission_contexts", "active")
            except KeyError:
                pass
        cop = self.cop_state_document()
        reports = self.database.list_documents("operator_reports") if self.database else []
        advisories = self.database.list_documents("cop_advisories") if self.database else []
        own_reports = [report for report in reports if report.get("reporter_id") == reporter_id]
        own_report_ids = {str(report["id"]) for report in own_reports}
        own_track = next(
            (
                track
                for track in cop.get("tracks", [])
                if track.get("entity_id") == reporter_id or track.get("label") == reporter_id
            ),
            None,
        )
        focus_label = (
            (own_track or {}).get("location")
            or (own_reports[-1] if own_reports else {}).get("location")
            or next(iter(mission.get("routes", [])), None)
            or next(iter(mission.get("named_areas", [])), None)
            or "Local operator area"
        )
        local_tracks = [
            track
            for track in cop.get("tracks", [])
            if track.get("entity_id") == reporter_id
            or track.get("label") == reporter_id
            or track.get("location") == focus_label
        ]
        local_reports = [
            report
            for report in reports
            if report.get("reporter_id") == reporter_id or report.get("location") == focus_label
        ]
        advisory_inbox = [
            advisory
            for advisory in advisories
            if advisory.get("recipient_id") == reporter_id
            or own_report_ids.intersection(str(item) for item in advisory.get("related_report_ids", []))
        ][-8:]

        markers: list[dict[str, object]] = []
        for track in local_tracks[:4]:
            markers.append(
                self._operator_map_marker(
                    marker_id=str(track.get("entity_id", track.get("label", "track"))),
                    label=str(track.get("label", "Track")),
                    kind="track",
                    status=str(track.get("lifecycle", track.get("status", "active"))),
                    confidence=float(track.get("confidence", 0.0)),
                    summary=str(track.get("location", focus_label)),
                    related_id=str(track.get("entity_id", "")),
                )
            )
        for report in local_reports[-4:]:
            markers.append(
                self._operator_map_marker(
                    marker_id=str(report.get("id", "report")),
                    label=str(report.get("report_type", "report")).replace("_", " "),
                    kind="report",
                    status=str(report.get("review_state", "new")),
                    confidence=float(report.get("confidence", 0.0)),
                    summary=str(report.get("summary", "")),
                    related_id=str(report.get("id", "")),
                )
            )
        for advisory in advisory_inbox[-3:]:
            markers.append(
                self._operator_map_marker(
                    marker_id=str(advisory.get("id", "advisory")),
                    label="Advisory",
                    kind="advisory",
                    status="human_review_required",
                    confidence=float(advisory.get("confidence", 0.0)),
                    summary=str(advisory.get("summary", "")),
                    related_id=str(advisory.get("id", "")),
                )
            )
        if not markers:
            markers.append(
                self._operator_map_marker(
                    marker_id=f"focus-{reporter_id or 'operator'}",
                    label=str(focus_label),
                    kind="focus",
                    status="monitoring",
                    confidence=0.0,
                    summary="No local tracks or advisories yet. Synthetic monitoring is ready.",
                    related_id="",
                )
            )

        status = "ready"
        if advisory_inbox:
            status = "advisories_waiting"
        elif own_reports:
            status = "monitoring"

        return {
            "operator_workspace": {
                "reporter_id": reporter_id,
                "device_id": device_id or "operator-mini-device",
                "status": status,
                "sync_mode": "synthetic_shadow_mode",
                "local_cop": {
                    "name": "Local Operator COP",
                    "focus_label": focus_label,
                    "tracks": local_tracks[:4],
                    "markers": markers,
                    "track_count": len(local_tracks),
                    "report_count": len(own_reports),
                    "advisory_count": len(advisory_inbox),
                },
                "mission": {
                    "id": mission.get("id"),
                    "mission_statement": mission.get("mission_statement", "No local mission context loaded."),
                    "routes": list(mission.get("routes", [])),
                    "named_areas": list(mission.get("named_areas", [])),
                    "timeline": list(mission.get("timeline", [])),
                },
                "recent_reports": own_reports[-6:],
                "advisory_inbox": advisory_inbox,
                "quick_actions": self._operator_quick_actions(),
                "guardrails": [
                    "JINX-Operator Mini is an advisory reporting surface only.",
                    "Only human operators create or acknowledge field reports.",
                    "Do not treat JINX responses as commands, orders, or targeting decisions.",
                ],
            }
        }

    def operator_brain_thread_document(self, reporter_id: str) -> dict[str, object]:
        messages = self.database.list_documents("brain_chat_messages") if self.database else []
        filtered = [
            message
            for message in messages
            if message.get("question", {}).get("user_id") == reporter_id
            or message.get("question", {}).get("role") == "operator"
        ]
        return {"messages": filtered[-8:]}

    def identity_users_document(self) -> dict[str, object]:
        self._ensure_governance_state()
        users = self.database.list_documents("identity_users") if self.database else ()
        sessions = self.database.list_documents("auth_sessions") if self.database else ()
        return {
            "identity": {
                "users": list(users),
                "roles": [
                    {
                        "name": role.name,
                        "description": role.description,
                        "permissions": sorted(role.permissions),
                    }
                    for role in self.access_control.roles.values()
                ],
                "active_session_count": sum(
                    1 for session in sessions if session.get("status") == "active"
                ),
            }
        }

    def register_identity_user(
        self,
        username: str,
        display_name: str,
        roles: tuple[str, ...],
        default_package: str = "operator",
        reporter_id: str = "",
        device_id: str = "",
    ) -> dict[str, object]:
        self._ensure_governance_state()
        if self.database is None:
            raise ValueError("database is required for identity registration")
        if not username:
            raise ValueError("username is required")
        if not display_name:
            raise ValueError("display_name is required")
        if not roles:
            raise ValueError("roles are required")
        unknown_roles = [role for role in roles if role not in self.access_control.roles]
        if unknown_roles:
            raise ValueError(f"unknown roles: {', '.join(sorted(unknown_roles))}")
        existing = next(
            (
                document
                for document in self.database.list_documents("identity_users")
                if document.get("username") == username
            ),
            None,
        )
        document = {
            "id": existing["id"] if existing else f"user-{uuid4().hex[:12]}",
            "username": username,
            "display_name": display_name,
            "roles": list(roles),
            "default_package": default_package,
            "reporter_id": reporter_id or username,
            "device_id": device_id or f"{default_package}-device",
            "active": True,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self.database.save_document("identity_users", document["id"], document)
        self._append_timeline(
            "identity_user",
            f"Identity user {username} registered or updated.",
            {"user_id": document["id"], "default_package": default_package},
        )
        return {"user": document}

    def issue_auth_session(
        self,
        username: str,
        package: str,
        reporter_id: str = "",
        device_id: str = "",
    ) -> dict[str, object]:
        self._ensure_governance_state()
        if self.database is None:
            raise ValueError("database is required for auth sessions")
        user = self._identity_user_by_username(username)
        if not self.package_license_allows(package, username):
            raise PermissionError(f"user {username} is not licensed for package {package}")
        permissions = sorted(self._permissions_for_roles(tuple(user.get("roles", ()))))
        session_id = f"session-{uuid4().hex[:16]}"
        license_document = self._package_license_for(package)
        document = {
            "id": session_id,
            "username": user["username"],
            "display_name": user["display_name"],
            "roles": list(user.get("roles", ())),
            "permissions": permissions,
            "package": package,
            "reporter_id": reporter_id or user.get("reporter_id") or username,
            "device_id": device_id or user.get("device_id") or f"{package}-device",
            "status": "active",
            "auth_mode": "synthetic_local_session",
            "license_active": bool(license_document.get("active", False)),
            "simulation_only": bool(license_document.get("simulation_only", True)),
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(hours=12)).isoformat(),
        }
        self.database.save_document("auth_sessions", session_id, document)
        self._append_timeline(
            "auth_session",
            f"Session issued for {username} on package {package}.",
            {"session_id": session_id, "package": package},
        )
        return {"session": document}

    def auth_session_document(self, session_id: str = "") -> dict[str, object]:
        self._ensure_governance_state()
        if self.database is None or not session_id:
            return {"session": None}
        try:
            return {"session": self.database.get_document("auth_sessions", session_id)}
        except KeyError:
            return {"session": None}

    def revoke_auth_session(self, session_id: str = "") -> dict[str, object]:
        self._ensure_governance_state()
        if self.database is None or not session_id:
            return {"session": None}
        session = self.auth_session_document(session_id).get("session")
        if not session:
            return {"session": None}
        document = {
            **session,
            "status": "inactive",
            "ended_at": datetime.now(UTC).isoformat(),
        }
        self.database.save_document("auth_sessions", session_id, document)
        self._append_timeline(
            "auth_session",
            f"Session revoked for {document['username']} on package {document['package']}.",
            {"session_id": session_id, "package": str(document.get("package", ""))},
        )
        return {"session": document}

    def license_state_document(self) -> dict[str, object]:
        self._ensure_governance_state()
        licenses = self.database.list_documents("package_licenses") if self.database else ()
        return {
            "licenses": list(licenses),
            "summary": {
                "active_packages": sum(1 for document in licenses if document.get("active")),
                "controlled_real_adapters_enabled": sum(
                    1 for document in licenses if document.get("controlled_real_adapters_enabled")
                ),
            },
        }

    def upsert_package_license(
        self,
        package: str,
        active: bool,
        authorized_users: tuple[str, ...],
        notes: str = "",
        controlled_real_adapters_enabled: bool = False,
    ) -> dict[str, object]:
        self._ensure_governance_state()
        if self.database is None:
            raise ValueError("database is required for package licenses")
        document = self._package_license_for(package)
        document.update(
            {
                "active": active,
                "authorized_users": list(authorized_users),
                "notes": notes,
                "controlled_real_adapters_enabled": controlled_real_adapters_enabled,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        self.database.save_document("package_licenses", package, document)
        self._append_timeline(
            "license_update",
            f"Package {package} license updated.",
            {"package": package, "active": str(active)},
        )
        return {"license": document}

    def entitlement_document(
        self,
        package: str,
        username: str = "",
        session_id: str = "",
    ) -> dict[str, object]:
        self._ensure_governance_state()
        license_document = self._package_license_for(package)
        policy = self._boundary_policy_for_package(package)
        session = self.auth_session_document(session_id).get("session") if session_id else None
        return {
            "entitlement": {
                "package": package,
                "license_active": bool(license_document.get("active", False)),
                "authorized_for_user": self.package_license_allows(package, username) if username else bool(license_document.get("active", False)),
                "authorized_users": list(license_document.get("authorized_users", ())),
                "simulation_only": bool(license_document.get("simulation_only", True)),
                "controlled_real_adapters_enabled": bool(
                    license_document.get("controlled_real_adapters_enabled", False)
                ),
                "denied_permission_prefixes": list(policy.get("denied_permission_prefixes", ())),
                "session_id": session.get("id") if session else None,
            }
        }

    def boundary_controls_document(self) -> dict[str, object]:
        self._ensure_governance_state()
        policy_decisions = self.database.list_documents("policy_decisions") if self.database else ()
        redactions = [
            record
            for record in (self.database.list_documents("audit_records") if self.database else ())
            if record.get("event_type") == "boundary_redaction"
        ]
        packages = []
        for document in self.database.list_documents("package_licenses") if self.database else ():
            policy = self._boundary_policy_for_package(str(document.get("package", "")))
            packages.append(
                {
                    "package": document.get("package"),
                    "active": document.get("active"),
                    "authorized_users": list(document.get("authorized_users", ())),
                    "simulation_only": document.get("simulation_only", True),
                    "denied_permission_prefixes": list(policy.get("denied_permission_prefixes", ())),
                    "summary": policy.get("summary", ""),
                }
            )
        return {
            "boundary_controls": {
                "packages": packages,
                "recent_redactions": list(redactions)[-8:],
                "recent_policy_denials": [
                    record for record in policy_decisions if not record.get("allowed", True)
                ][-8:],
            }
        }

    def adapter_registry_document(self) -> dict[str, object]:
        self._ensure_governance_state()
        adapters = (
            [self._evaluated_adapter_document(document) for document in self.database.list_documents("adapter_manifests")]
            if self.database
            else []
        )
        return {
            "adapters": adapters,
            "summary": {
                "enabled": sum(1 for document in adapters if document.get("enabled")),
                "authorized_live": sum(
                    1
                    for document in adapters
                    if document.get("data_mode") == DataMode.LIVE_CONTROLLED_ADAPTER.value
                    and document.get("explicitly_authorized")
                ),
                "blocked": sum(1 for document in adapters if document.get("status") == "blocked"),
            },
        }

    def update_adapter_state(
        self,
        adapter_id: str,
        action: str,
        explicitly_authorized: bool | None = None,
        enabled: bool | None = None,
        data_mode: str = "",
    ) -> dict[str, object]:
        self._ensure_governance_state()
        if self.database is None:
            raise ValueError("database is required for adapter control")
        document = self._adapter_document(adapter_id)
        if action == "authorize":
            document["explicitly_authorized"] = bool(explicitly_authorized)
        elif action == "activate":
            document["enabled"] = bool(enabled if enabled is not None else True)
        elif action == "set_mode":
            document["data_mode"] = DataMode(data_mode or document["data_mode"]).value
        else:
            raise ValueError(f"unsupported adapter action: {action}")
        evaluated = self._evaluated_adapter_document(document)
        self.database.save_document("adapter_manifests", adapter_id, evaluated)
        self._append_timeline(
            "adapter_control",
            f"Adapter {evaluated['name']} updated via {action}.",
            {"adapter_id": adapter_id, "status": evaluated["status"]},
        )
        return {"adapter": evaluated}

    def simulation_dashboard_document(self) -> dict[str, object]:
        library = self.simulation_library_document()["simulation_scenarios"]
        runs = self.simulation_runs_document()["simulation_runs"]
        control = self.simulation_control_document()["simulation_control"]
        latest_run = runs[-1] if runs else None
        mismatch_count = sum(1 for run in runs if run.get("result_state", "matched") != "matched")
        return {
            "simulation": {
                "mode": "deterministic_shadow_mode",
                "status": control.get("playback_state", "idle"),
                "library_count": len(library),
                "custom_scenario_count": sum(1 for scenario in library if scenario.get("source") == "custom"),
                "run_count": len(runs),
                "mismatch_count": mismatch_count,
                "latest_run": latest_run,
                "recent_runs": runs[-6:],
                "control": control,
                "guardrails": [
                    "Simulation data remains synthetic and clearly labeled.",
                    "Scenario replay remains advisory and does not touch live adapters.",
                    "Expected-vs-actual results support human review and regression testing.",
                ],
            }
        }

    def simulation_library_document(self) -> dict[str, object]:
        builtin = [self._simulation_scenario_document_from_pack(pack) for pack in default_c5isr_scenario_packs()]
        custom = list(self.database.list_documents("simulation_scenarios")) if self.database else []
        scenarios = sorted(
            builtin + custom,
            key=lambda scenario: (str(scenario.get("source", "")) != "built_in", str(scenario.get("name", ""))),
        )
        return {"simulation_scenarios": scenarios}

    def simulation_runs_document(self) -> dict[str, object]:
        return {"simulation_runs": self.database.list_documents("simulation_runs") if self.database else []}

    def simulation_control_document(self) -> dict[str, object]:
        if self.database is None:
            return {"simulation_control": self._default_simulation_control()}
        try:
            control = self.database.get_document("simulation_control", "active")
        except KeyError:
            control = self._save_simulation_control(self._default_simulation_control())
        return {"simulation_control": control}

    def create_simulation_scenario(
        self,
        name: str,
        summary: str,
        inject_script: str,
        expected_outputs: tuple[str, ...],
    ) -> dict[str, object]:
        if self.database is None:
            raise ValueError("database is required for simulation scenarios")
        scenario_id = f"sim-scenario-{uuid4()}"
        injects = self._parse_simulation_inject_script(inject_script)
        document = {
            "id": scenario_id,
            "name": name,
            "summary": summary,
            "source": "custom",
            "scenario_type": "mixed_inject",
            "injects": injects,
            "expected_outputs": list(expected_outputs),
            "synthetic": True,
            "duration_seconds": max((inject["offset_seconds"] for inject in injects), default=0),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.database.save_document("simulation_scenarios", scenario_id, document)
        self._append_timeline(
            "simulation_scenario",
            f"Custom simulation scenario {name} saved.",
            {"scenario_id": scenario_id},
        )
        return {"simulation_scenario": document}

    def update_simulation_control(
        self,
        action: str,
        scenario_id: str = "",
        offset_seconds: int = 0,
    ) -> dict[str, object]:
        if action not in {"select", "play", "pause", "reset", "step", "scrub"}:
            raise ValueError(f"unsupported simulation control action: {action}")
        if self.database is None:
            raise ValueError("database is required for simulation control")
        control = self.simulation_control_document()["simulation_control"]
        scenario = self._load_simulation_scenario_document(scenario_id or control.get("selected_scenario_id", ""))

        if action == "select":
            control.update(self._control_state_for_scenario(scenario, playback_state="idle", action="select"))
        elif action == "play":
            run = self._run_simulation_document(scenario)
            control.update(
                self._control_state_for_scenario(
                    scenario,
                    playback_state="completed",
                    action="play",
                    offset_seconds=int(scenario.get("duration_seconds", 0)),
                    latest_run_id=run["simulation_run"]["id"],
                )
            )
            control = self._save_simulation_control(control)
            return {"simulation_control": control, "simulation_run": run["simulation_run"]}
        elif action == "pause":
            control["playback_state"] = "paused"
            control["last_action"] = "pause"
        elif action == "reset":
            control.update(self._control_state_for_scenario(scenario, playback_state="idle", action="reset"))
        elif action == "step":
            next_offset = self._next_simulation_offset(scenario, int(control.get("current_offset_seconds", 0)))
            control.update(
                self._control_state_for_scenario(
                    scenario,
                    playback_state="stepped",
                    action="step",
                    offset_seconds=next_offset,
                )
            )
        elif action == "scrub":
            control.update(
                self._control_state_for_scenario(
                    scenario,
                    playback_state="scrubbed",
                    action="scrub",
                    offset_seconds=max(0, offset_seconds),
                )
            )

        control = self._save_simulation_control(control)
        return {"simulation_control": control}

    def run_simulation_scenario(self, scenario_id: str) -> dict[str, object]:
        scenario = self._load_simulation_scenario_document(scenario_id)
        return self._run_simulation_document(scenario)

    def run_c5isr_scenario_pack(self, scenario_id: str) -> dict[str, object]:
        pack = self._find_scenario_pack(scenario_id)
        return self._run_simulation_document(self._simulation_scenario_document_from_pack(pack))

    def _bounded_core_reachback(self) -> dict[str, object]:
        if self.database is None:
            return {}
        try:
            mission = self.database.get_document("mission_contexts", "active")
        except KeyError:
            mission = {"id": None}
        try:
            cop = self.database.get_document("cop_states", "latest")
        except KeyError:
            cop = {"id": None, "tracks": []}
        return {
            "mission": mission,
            "cop": cop,
            "conflicts": self.database.list_documents("conflicts")[-5:],
            "recommendations": self.database.list_documents("recommendations")[-5:],
            "mission_impacts": self.database.list_documents("mission_impacts")[-5:],
            "isr_feeds": self.database.list_documents("isr_feeds")[-5:],
            "net": {
                "network_plans": self.database.list_documents("network_plans")[-5:],
                "network_issues": self.database.list_documents("network_issues")[-5:],
                "network_validation_runs": self.database.list_documents("network_validation_runs")[-5:],
            },
            "modules": [module["name"] for module in self.module_boundary_document()["modules"]],
        }

    def _brain_bounded_context(self) -> BoundedBrainContext | None:
        raw_context = self._bounded_core_reachback()
        if not raw_context:
            return None
        return self.brain_context_builder.build(
            raw_context,
            allowed_modules=self._licensed_module_names(),
            source="jinx-core.reachback",
        )

    def _licensed_module_names(self) -> frozenset[str]:
        return frozenset(module["name"] for module in self.module_boundary_document()["modules"])

    def _refresh_brain_systems(self) -> None:
        repository = build_synthetic_doctrine_repository()
        for record in self._doctrine_records_from_database():
            try:
                repository.add(record)
            except ValueError:
                continue
        self.brain_repository = repository
        self.brain_chat = BrainChatEngine(self.brain_repository)
        self.core_reasoning = CoreReasoningWorkflow(
            self.router,
            recommendation_engine=CoreRecommendationEngine(doctrine_repository=self.brain_repository),
        )

    def _doctrine_records_from_database(self) -> tuple[DoctrineRecord, ...]:
        if self.database is None:
            return ()
        records: list[DoctrineRecord] = []
        for document in self.database.list_documents("doctrine_library"):
            try:
                records.append(
                    DoctrineRecord(
                        title=str(document["title"]),
                        scope=DoctrineScope(str(document["scope"])),
                        summary=str(document["summary"]),
                        source=str(document["source"]),
                        applicability=tuple(str(item) for item in document.get("applicability", ()) if str(item)),
                        restrictions=tuple(str(item) for item in document.get("restrictions", ()) if str(item)),
                        tags=frozenset(str(item) for item in document.get("tags", ()) if str(item)),
                        id=str(document["id"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return tuple(records)

    def _save_evidence_pack(
        self,
        source_kind: str,
        source_id: str,
        source_module: str,
        package_scope: str,
        title: str,
        summary: str,
        confidence_value: float,
        recommended_review_role: str,
        related_ids: tuple[str, ...] = (),
        provenance_refs: tuple[str, ...] = (),
        assumptions: tuple[str, ...] = (),
        uncertainty: tuple[str, ...] = (),
        redactions: tuple[str, ...] = (),
        brain_references: tuple[str, ...] = (),
        allowed_actions: tuple[str, ...] = (),
        disallowed_actions: tuple[str, ...] = (),
        tags: tuple[str, ...] = (),
        simulation_flag: bool = True,
    ) -> dict[str, object] | None:
        if self.database is None:
            return None
        document = {
            "id": f"evidence-{source_kind}-{source_id}",
            "source_kind": source_kind,
            "source_id": source_id,
            "source_module": source_module,
            "package_scope": package_scope,
            "memory_compartment": self._memory_compartment_for_package(package_scope),
            "title": title,
            "summary": summary,
            "confidence": round(confidence_value, 2),
            "confidence_band": self._confidence_band(confidence_value),
            "recommended_review_role": recommended_review_role,
            "related_ids": list(related_ids),
            "provenance_refs": list(provenance_refs),
            "assumptions": list(assumptions),
            "uncertainty": list(uncertainty),
            "redactions": list(redactions),
            "brain_references": list(brain_references),
            "allowed_actions": list(allowed_actions),
            "disallowed_actions": list(disallowed_actions),
            "tags": sorted(set(tags)),
            "simulation_flag": simulation_flag,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.database.save_document("evidence_packs", document["id"], document)
        return document

    @staticmethod
    def _confidence_band(value: float) -> str:
        if value >= 0.75:
            return "high"
        if value >= 0.4:
            return "medium"
        return "low"

    @staticmethod
    def _default_reviewer_for_role(role: str) -> str:
        mapping = {
            "system_administrator": "systemadministrator",
            "c5isr_manager": "c5isr-manager-alpha",
            "network_manager": "net-manager-alpha",
            "integrator_operator": "integrator-alpha",
            "intel_analyst": "intel-alpha",
            "simulation_operator": "sim-operator-alpha",
            "operator": "operator-alpha",
            "auditor": "auditor-alpha",
            "commander": "commander-alpha",
            "human reviewer": "systemadministrator",
        }
        return mapping.get(role, "systemadministrator")

    @staticmethod
    def _priority_for_severity(severity: str) -> str:
        mapping = {
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low",
        }
        return mapping.get(severity, "medium")

    @staticmethod
    def _due_label_for_priority(priority: str) -> str:
        mapping = {
            "critical": "Immediate",
            "high": "This hour",
            "medium": "This shift",
            "low": "When available",
        }
        return mapping.get(priority, "This shift")

    def _sync_review_tasks(self) -> None:
        if self.database is None:
            return
        for report in self.database.list_documents("operator_reports"):
            self._upsert_review_task(
                task_id=f"review-operator-report-{report['id']}",
                document={
                    "source_kind": "operator_report",
                    "source_id": report["id"],
                    "package_scope": "c5isr",
                    "title": f"Operator report {report.get('report_type', 'report')}",
                    "summary": report.get("summary", ""),
                    "severity": report.get("severity", "medium"),
                    "confidence": report.get("confidence", 0.0),
                    "assigned_role": "c5isr_manager",
                    "evidence_pack_ids": [f"evidence-operator_report-{report['id']}"],
                    "related_ids": [report["id"]],
                    "provenance_refs": [report["id"]],
                },
            )
        for conflict in self.database.list_documents("conflicts"):
            self._upsert_review_task(
                task_id=f"review-conflict-{conflict['id']}",
                document={
                    "source_kind": "conflict",
                    "source_id": conflict["id"],
                    "package_scope": "c5isr",
                    "title": f"Conflict {conflict.get('conflict_type', 'packet')}",
                    "summary": conflict.get("explanation", ""),
                    "severity": "high",
                    "confidence": conflict.get("confidence", 0.0),
                    "assigned_role": conflict.get("recommended_review_role", "c5isr_manager"),
                    "evidence_pack_ids": [f"evidence-conflict-{conflict['id']}"],
                    "related_ids": list(conflict.get("conflicting_items", ())),
                    "provenance_refs": [f"prov-conflict-{conflict['id']}-1"],
                },
            )
        for impact in self.database.list_documents("mission_impacts"):
            self._upsert_review_task(
                task_id=f"review-mission-impact-{impact['id']}",
                document={
                    "source_kind": "mission_impact",
                    "source_id": impact["id"],
                    "package_scope": "c5isr",
                    "title": f"Mission impact {impact.get('impacted_area', 'review')}",
                    "summary": impact.get("summary", ""),
                    "severity": "medium",
                    "confidence": impact.get("confidence", 0.0),
                    "assigned_role": impact.get("recommended_review_role", "c5isr_manager"),
                    "evidence_pack_ids": [f"evidence-mission_impact-{impact['id']}"],
                    "related_ids": list(impact.get("source_event_ids", ())),
                    "provenance_refs": [f"prov-mission_impact-{impact['id']}-1"],
                },
            )
        for issue in self.database.list_documents("network_issues"):
            self._upsert_review_task(
                task_id=f"review-network-issue-{issue['id']}",
                document={
                    "source_kind": "network_issue",
                    "source_id": issue["id"],
                    "package_scope": "net",
                    "title": f"NET issue {issue.get('issue_type', 'review')}",
                    "summary": issue.get("summary", ""),
                    "severity": issue.get("severity", "medium"),
                    "confidence": issue.get("confidence", 0.0),
                    "assigned_role": issue.get("recommended_review_role", "network_manager"),
                    "evidence_pack_ids": [f"evidence-network_issue-{issue['id']}"],
                    "related_ids": [issue["id"], issue.get("plan_id", "")],
                    "provenance_refs": [f"prov-network_issue-{issue['id']}-1"],
                },
            )
        for notice in self.database.list_documents("intel_module_notices"):
            self._upsert_review_task(
                task_id=f"review-intel-notice-{notice['id']}",
                document={
                    "source_kind": "intel_module_notice",
                    "source_id": notice["id"],
                    "package_scope": "intel",
                    "title": f"INTEL notice {notice.get('module', 'review')}",
                    "summary": notice.get("summary", ""),
                    "severity": "medium",
                    "confidence": notice.get("confidence", 0.0),
                    "assigned_role": "intel_analyst",
                    "evidence_pack_ids": [f"evidence-intel_notice-{notice['id']}"],
                    "related_ids": [notice["id"], notice.get("intel_summary_id", ""), notice.get("intel_impact_id", "")],
                    "provenance_refs": [notice.get("intel_summary_id", ""), notice.get("intel_impact_id", "")],
                },
            )
        for proposal in self.database.list_documents("learning_proposals"):
            self._upsert_review_task(
                task_id=f"review-learning-proposal-{proposal['id']}",
                document={
                    "source_kind": "learning_proposal",
                    "source_id": proposal["id"],
                    "package_scope": "full",
                    "title": "BRAIN lesson promotion review",
                    "summary": proposal.get("summary", ""),
                    "severity": "low",
                    "confidence": 0.5,
                    "assigned_role": proposal.get("required_reviewer_role", "system_administrator"),
                    "evidence_pack_ids": [f"evidence-learning_proposal-{proposal['id']}"],
                    "related_ids": [proposal["id"], *list(proposal.get("evidence_refs", ()))],
                    "provenance_refs": list(proposal.get("evidence_refs", ())),
                },
            )
        for run in self.database.list_documents("adapter_runs"):
            if run.get("status") == "completed":
                continue
            self._upsert_review_task(
                task_id=f"review-adapter-run-{run['id']}",
                document={
                    "source_kind": "adapter_run",
                    "source_id": run["id"],
                    "package_scope": "full",
                    "title": f"Adapter run {run.get('adapter_name', run['adapter_id'])}",
                    "summary": run.get("summary", ""),
                    "severity": "medium",
                    "confidence": 0.42,
                    "assigned_role": "system_administrator",
                    "evidence_pack_ids": [f"evidence-adapter_run-{run['id']}"],
                    "related_ids": [run["id"], run.get("adapter_id", "")],
                    "provenance_refs": [run.get("adapter_id", "")],
                },
            )

    def _upsert_review_task(self, task_id: str, document: dict[str, object]) -> None:
        if self.database is None:
            return
        now = datetime.now(UTC).isoformat()
        existing = None
        try:
            existing = self.database.get_document("review_tasks", task_id)
        except KeyError:
            existing = None
        state = str(existing.get("state", "new")) if existing else "new"
        severity = str(document.get("severity", existing.get("severity", "medium") if existing else "medium"))
        assigned_role = str(
            existing.get("assigned_role", document.get("assigned_role", "system_administrator")) if existing else document.get("assigned_role", "system_administrator")
        )
        priority = str(existing.get("priority", self._priority_for_severity(severity)) if existing else self._priority_for_severity(severity))
        merged = {
            "id": task_id,
            "state": state,
            "history": list(existing.get("history", [])) if existing else [],
            "acknowledged_by": existing.get("acknowledged_by") if existing else None,
            "reviewed_by": existing.get("reviewed_by") if existing else None,
            "last_note": existing.get("last_note", "") if existing else "",
            "assigned_reviewer": existing.get("assigned_reviewer", self._default_reviewer_for_role(assigned_role)) if existing else self._default_reviewer_for_role(assigned_role),
            "escalation_state": existing.get("escalation_state", "none") if existing else "none",
            "priority": priority,
            "due_label": existing.get("due_label", self._due_label_for_priority(priority)) if existing else self._due_label_for_priority(priority),
            "review_lane": existing.get("review_lane", document.get("package_scope", "full")) if existing else document.get("package_scope", "full"),
            "created_at": existing.get("created_at", now) if existing else now,
            "updated_at": now,
            **document,
        }
        self.database.save_document("review_tasks", task_id, merged)

    def _apply_review_state_to_source(
        self,
        task: dict[str, object],
        state: str,
        reviewer_id: str,
        note: str,
    ) -> None:
        if self.database is None:
            return
        source_kind = str(task.get("source_kind", ""))
        source_id = str(task.get("source_id", ""))
        if source_kind == "operator_report":
            mapped_state = {
                "acknowledged": "under_review",
                "validated": "validated",
                "needs_more_info": "needs_more_info",
                "rejected": "closed",
                "closed": "closed",
                "new": "new",
            }[state]
            self.review_operator_report(source_id, mapped_state, reviewer_id, note)
            return
        collection_map = {
            "conflict": "conflicts",
            "mission_impact": "mission_impacts",
            "network_issue": "network_issues",
            "intel_module_notice": "intel_module_notices",
            "learning_proposal": "learning_proposals",
            "adapter_run": "adapter_runs",
        }
        collection = collection_map.get(source_kind)
        if not collection:
            return
        document = self.database.get_document(collection, source_id)
        document["review_state"] = state
        document["reviewed_by"] = reviewer_id
        document["review_note"] = note
        document["reviewed_at"] = datetime.now(UTC).isoformat()
        if source_kind == "learning_proposal":
            document["review_status"] = "approved" if state == "validated" else "rejected" if state == "rejected" else document.get("review_status", "proposed")
        self.database.save_document(collection, source_id, document)

    def _persist_memory_record(
        self,
        compartment: str,
        package_scope: str,
        title: str,
        summary: str,
        tags: tuple[str, ...],
        source_kind: str,
        source_id: str,
        created_by: str,
        provenance_refs: tuple[str, ...] = (),
        review_state: str = "captured",
    ) -> dict[str, object]:
        if self.database is None:
            raise ValueError("database is required for memory records")
        document = {
            "id": f"memory-{uuid4().hex[:12]}",
            "compartment": compartment,
            "package_scope": package_scope,
            "title": title,
            "summary": summary,
            "tags": list(tags),
            "source_kind": source_kind,
            "source_id": source_id,
            "created_by": created_by,
            "provenance_refs": list(provenance_refs),
            "review_state": review_state,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.database.save_document("compartment_memories", document["id"], document)
        return document

    @staticmethod
    def _memory_compartment_for_package(package_scope: str) -> str:
        mapping = {
            "c5isr": "c5isr.package",
            "net": "net.package",
            "intel": "intel.package",
            "sim": "sim.package",
            "operator": "operator.package",
            "full": "core.shared",
        }
        return mapping.get(package_scope, "core.shared")

    @staticmethod
    def _matches_recall_query(query_text: str, record: dict[str, object], fields: tuple[str, ...]) -> bool:
        if not query_text:
            return True
        haystack = " ".join(str(record.get(field, "")) for field in fields).lower()
        tags = " ".join(str(item) for item in record.get("tags", ())).lower()
        return query_text in haystack or query_text in tags

    def _build_audit_replay_document(
        self,
        focus_id: str = "",
        limit: int = 12,
        package_scope: str = "",
        source_kind: str = "",
        query: str = "",
    ) -> dict[str, object]:
        self._sync_review_tasks()
        self._sync_audit_ledger()
        self._sync_fabric_ledger()
        self._sync_provenance_ledger()
        evidence = list(self.database.list_documents("evidence_packs")) if self.database else []
        review_tasks = list(self.database.list_documents("review_tasks")) if self.database else []
        memories = list(self.database.list_documents("compartment_memories")) if self.database else []
        timeline = list(self.database.list_documents("timeline")) if self.database else []
        audits = list(self.database.list_documents("audit_records")) if self.database else []
        policy_decisions = list(self.database.list_documents("policy_decisions")) if self.database else []
        fabric = list(self.database.list_documents("fabric_messages")) if self.database else []
        query_text = query.strip().lower()
        if package_scope:
            evidence = [record for record in evidence if record.get("package_scope") in {package_scope, "full"}]
            review_tasks = [record for record in review_tasks if record.get("package_scope") in {package_scope, "full"}]
            memories = [record for record in memories if record.get("package_scope") in {package_scope, "full"}]
        if source_kind:
            evidence = [record for record in evidence if record.get("source_kind") == source_kind]
            review_tasks = [record for record in review_tasks if record.get("source_kind") == source_kind]
            memories = [record for record in memories if record.get("source_kind") == source_kind]
        if query_text:
            evidence = [
                record
                for record in evidence
                if self._matches_recall_query(query_text, record, ("title", "summary", "source_kind", "recommended_review_role"))
            ]
            review_tasks = [
                record
                for record in review_tasks
                if self._matches_recall_query(query_text, record, ("title", "summary", "state", "assigned_role", "assigned_reviewer"))
            ]
            memories = [
                record
                for record in memories
                if self._matches_recall_query(query_text, record, ("title", "summary", "compartment", "source_kind"))
            ]
            timeline = [
                record
                for record in timeline
                if query_text in str(record.get("summary", "")).lower() or query_text in str(record.get("kind", "")).lower()
            ]
            audits = [
                record
                for record in audits
                if query_text in str(record.get("summary", "")).lower()
            ]
            policy_decisions = [
                record
                for record in policy_decisions
                if query_text in str(record.get("summary", "")).lower()
                or query_text in str(record.get("source_module", "")).lower()
                or query_text in str(record.get("destination", "")).lower()
            ]
            fabric = [
                record
                for record in fabric
                if query_text in str(record.get("topic", "")).lower()
                or query_text in str(record.get("source_module", "")).lower()
                or query_text in str(record.get("destination", "")).lower()
            ]
        if focus_id:
            evidence = [
                record
                for record in evidence
                if focus_id == record.get("source_id")
                or focus_id in record.get("related_ids", [])
                or focus_id in record.get("provenance_refs", [])
            ]
            review_tasks = [
                record
                for record in review_tasks
                if focus_id == record.get("source_id") or focus_id in record.get("related_ids", [])
            ]
            memories = [
                record
                for record in memories
                if focus_id == record.get("source_id") or focus_id in record.get("provenance_refs", [])
            ]
            timeline = [
                record
                for record in timeline
                if focus_id == record.get("id") or focus_id in str(record.get("metadata", {}))
            ]
            audits = [
                record
                for record in audits
                if focus_id in record.get("summary", "") or focus_id in str(record.get("metadata", {}))
            ]
            policy_decisions = [
                record
                for record in policy_decisions
                if focus_id in str(record.get("message_id", "")) or focus_id in record.get("summary", "")
            ]
            fabric = [
                record
                for record in fabric
                if focus_id == record.get("provenance_ref") or focus_id == record.get("message_id")
            ]
        package_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}
        review_state_counts: dict[str, int] = {}
        for record in evidence:
            package = str(record.get("package_scope", "full"))
            package_counts[package] = package_counts.get(package, 0) + 1
            kind = str(record.get("source_kind", "unknown"))
            source_counts[kind] = source_counts.get(kind, 0) + 1
        for record in review_tasks:
            state = str(record.get("state", "new"))
            review_state_counts[state] = review_state_counts.get(state, 0) + 1
        cross_reference_ids = sorted(
            {
                str(item)
                for record in evidence
                for item in [record.get("source_id", ""), *list(record.get("related_ids", ()))]
                if str(item)
            }
        )[:12]
        replay_id = f"replay-{uuid4().hex[:12]}"
        return {
            "id": replay_id,
            "focus_id": focus_id or "latest-platform-state",
            "generated_at": datetime.now(UTC).isoformat(),
            "drilldown": {
                "package_scope": package_scope or "all",
                "source_kind": source_kind or "all",
                "query": query,
                "matched_cross_references": cross_reference_ids,
            },
            "summary": {
                "timeline_events": len(timeline[-limit:]),
                "audit_records": len(audits[-limit:]),
                "policy_decisions": len(policy_decisions[-limit:]),
                "fabric_messages": len(fabric[-limit:]),
                "evidence_packs": len(evidence[-limit:]),
                "review_tasks": len(review_tasks[-limit:]),
                "memory_records": len(memories[-limit:]),
                "package_counts": package_counts,
                "source_kind_counts": source_counts,
                "review_state_counts": review_state_counts,
            },
            "timeline": timeline[-limit:],
            "audit_records": audits[-limit:],
            "policy_decisions": policy_decisions[-limit:],
            "fabric_messages": fabric[-limit:],
            "evidence_packs": evidence[-limit:],
            "review_tasks": review_tasks[-limit:],
            "memory_records": memories[-limit:],
            "guardrails": [
                "Replay is advisory reconstruction only.",
                "Replay does not create command authority or operational tasking.",
                "Synthetic, mock, open, or explicitly authorized data only.",
            ],
        }

    @staticmethod
    def _synthetic_provenance(module: str) -> ProvenanceRecord:
        return ProvenanceRecord(
            source="jinx-application-service",
            time_received=datetime.now(UTC),
            processed_by_module=module,
            transformations=("service_generated",),
            confidence=JINXApplicationService._synthetic_confidence(),
        )

    @staticmethod
    def _synthetic_confidence() -> ConfidenceScore:
        return ConfidenceScore(
            value=0.63,
            scale="0.0-1.0",
            rationale="Synthetic service-generated provenance confidence.",
            source_quality=0.62,
            recency_factor=0.8,
            corroboration_factor=0.25,
            contradiction_factor=0.08,
            completeness_factor=0.56,
        )

    def _ensure_governance_state(self) -> None:
        if self.database is None:
            return
        existing_users = {
            str(document.get("id", ""))
            for document in self.database.list_documents("identity_users")
        }
        for document in self._default_identity_user_documents():
            if document["id"] not in existing_users:
                self.database.save_document("identity_users", document["id"], document)

        existing_licenses = {
            str(document.get("package", ""))
            for document in self.database.list_documents("package_licenses")
        }
        for document in self._default_package_license_documents():
            if document["package"] not in existing_licenses:
                self.database.save_document("package_licenses", document["package"], document)

        existing_adapters = {
            str(document.get("id", ""))
            for document in self.database.list_documents("adapter_manifests")
        }
        for document in self._default_adapter_documents():
            if document["id"] not in existing_adapters:
                self.database.save_document("adapter_manifests", document["id"], document)

    def _default_identity_user_documents(self) -> tuple[dict[str, object], ...]:
        now = datetime.now(UTC).isoformat()
        return (
            {
                "id": "user-systemadministrator",
                "username": "systemadministrator",
                "display_name": "System Administrator",
                "roles": ["system_administrator"],
                "default_package": "full",
                "reporter_id": "systemadministrator",
                "device_id": "jinx-admin-console",
                "active": True,
                "updated_at": now,
            },
            {
                "id": "user-c5isr-manager-alpha",
                "username": "c5isr-manager-alpha",
                "display_name": "C5ISR Manager Alpha",
                "roles": ["c5isr_manager"],
                "default_package": "c5isr",
                "reporter_id": "c5isr-manager-alpha",
                "device_id": "jinx-c5isr-console",
                "active": True,
                "updated_at": now,
            },
            {
                "id": "user-net-manager-alpha",
                "username": "net-manager-alpha",
                "display_name": "NET Manager Alpha",
                "roles": ["network_manager"],
                "default_package": "net",
                "reporter_id": "net-manager-alpha",
                "device_id": "jinx-net-console",
                "active": True,
                "updated_at": now,
            },
            {
                "id": "user-integrator-alpha",
                "username": "integrator-alpha",
                "display_name": "Integrator Operator Alpha",
                "roles": ["integrator_operator"],
                "default_package": "integrator",
                "reporter_id": "integrator-alpha",
                "device_id": "jinx-integrator-console",
                "active": True,
                "updated_at": now,
            },
            {
                "id": "user-intel-alpha",
                "username": "intel-alpha",
                "display_name": "INTEL Analyst Alpha",
                "roles": ["intel_analyst"],
                "default_package": "intel",
                "reporter_id": "intel-alpha",
                "device_id": "jinx-intel-console",
                "active": True,
                "updated_at": now,
            },
            {
                "id": "user-sim-operator-alpha",
                "username": "sim-operator-alpha",
                "display_name": "Simulation Operator Alpha",
                "roles": ["simulation_operator"],
                "default_package": "sim",
                "reporter_id": "sim-operator-alpha",
                "device_id": "jinx-sim-console",
                "active": True,
                "updated_at": now,
            },
            {
                "id": "user-operator-alpha",
                "username": "operator-alpha",
                "display_name": "Operator Alpha",
                "roles": ["operator"],
                "default_package": "operator",
                "reporter_id": "operator-alpha",
                "device_id": "operator-mini-001",
                "active": True,
                "updated_at": now,
            },
            {
                "id": "user-auditor-alpha",
                "username": "auditor-alpha",
                "display_name": "Auditor Alpha",
                "roles": ["auditor"],
                "default_package": "full",
                "reporter_id": "auditor-alpha",
                "device_id": "jinx-audit-console",
                "active": True,
                "updated_at": now,
            },
        )

    def _default_package_license_documents(self) -> tuple[dict[str, object], ...]:
        now = datetime.now(UTC).isoformat()
        return (
            {
                "package": "full",
                "label": "Full JINX Package",
                "modules": ["core", "brain", "c5isr", "net", "intel", "sim", "bus"],
                "apps": ["/apps/ops", "/apps/c5isr", "/apps/net", "/apps/intel", "/apps/sim", "/apps/operator"],
                "active": True,
                "authorized_users": ["systemadministrator", "auditor-alpha", "c5isr-manager-alpha"],
                "simulation_only": True,
                "controlled_real_adapters_enabled": False,
                "notes": "Synthetic, shadow-mode, and administrative use only.",
                "updated_at": now,
            },
            {
                "package": "c5isr",
                "label": "JINX-C5ISR Package",
                "modules": ["core", "brain", "c5isr", "sim", "bus"],
                "apps": ["/apps/c5isr"],
                "active": True,
                "authorized_users": ["systemadministrator", "c5isr-manager-alpha"],
                "simulation_only": True,
                "controlled_real_adapters_enabled": False,
                "notes": "C5ISR advisory surface only.",
                "updated_at": now,
            },
            {
                "package": "net",
                "label": "JINX-NET Package",
                "modules": ["core", "brain", "net", "sim", "bus"],
                "apps": ["/apps/net"],
                "active": True,
                "authorized_users": ["systemadministrator", "net-manager-alpha"],
                "simulation_only": True,
                "controlled_real_adapters_enabled": False,
                "notes": "NET advisory and synthetic validation only.",
                "updated_at": now,
            },
            {
                "package": "integrator",
                "label": "JINX-Integrator Package",
                "modules": ["core", "brain", "integrator", "sim", "bus"],
                "apps": ["/apps/integrator"],
                "active": True,
                "authorized_users": ["systemadministrator", "integrator-alpha"],
                "simulation_only": True,
                "controlled_real_adapters_enabled": False,
                "notes": "Bounded message-family intake, normalization, and internal routing only.",
                "updated_at": now,
            },
            {
                "package": "intel",
                "label": "JINX-INTEL Package",
                "modules": ["core", "brain", "intel", "sim", "bus"],
                "apps": ["/apps/intel"],
                "active": True,
                "authorized_users": ["systemadministrator", "intel-alpha"],
                "simulation_only": True,
                "controlled_real_adapters_enabled": False,
                "notes": "INTEL contextualization only.",
                "updated_at": now,
            },
            {
                "package": "sim",
                "label": "JINX-SIM Package",
                "modules": ["core", "brain", "sim", "bus"],
                "apps": ["/apps/sim"],
                "active": True,
                "authorized_users": ["systemadministrator", "sim-operator-alpha", "c5isr-manager-alpha"],
                "simulation_only": True,
                "controlled_real_adapters_enabled": False,
                "notes": "Scenario rehearsal and replay only.",
                "updated_at": now,
            },
            {
                "package": "operator",
                "label": "JINX-Operator Mini Package",
                "modules": ["core", "brain", "c5isr", "bus"],
                "apps": ["/apps/operator"],
                "active": True,
                "authorized_users": ["systemadministrator", "operator-alpha"],
                "simulation_only": True,
                "controlled_real_adapters_enabled": False,
                "notes": "Phone-first field reporting surface.",
                "updated_at": now,
            },
        )

    def _default_adapter_documents(self) -> tuple[dict[str, object], ...]:
        now = datetime.now(UTC).isoformat()
        return (
            {
                "id": "adapter-sim-feed",
                "name": "SIM Feed Orchestrator",
                "adapter_type": "simulation_feed",
                "target_module": "jinx-sim",
                "permission": "audit:write",
                "data_mode": DataMode.SYNTHETIC.value,
                "safety_classification": SafetyClassification.SIMULATION.value,
                "supports_simulation": True,
                "explicitly_authorized": False,
                "enabled": True,
                "status": "enabled",
                "notes": "Primary simulation event source.",
                "updated_at": now,
            },
            {
                "id": "adapter-weather-open",
                "name": "Open Weather Context Stub",
                "adapter_type": "weather",
                "target_module": "jinx-intel",
                "permission": "mock_adapter:read",
                "data_mode": DataMode.OPEN.value,
                "safety_classification": SafetyClassification.MOCK_ADAPTER.value,
                "supports_simulation": True,
                "explicitly_authorized": False,
                "enabled": False,
                "status": "available",
                "notes": "Open-source weather placeholder.",
                "updated_at": now,
            },
            {
                "id": "adapter-geospatial-mock",
                "name": "Geospatial COP Stub",
                "adapter_type": "geospatial",
                "target_module": "jinx-c5isr",
                "permission": "mock_adapter:read",
                "data_mode": DataMode.MOCK.value,
                "safety_classification": SafetyClassification.MOCK_ADAPTER.value,
                "supports_simulation": True,
                "explicitly_authorized": False,
                "enabled": False,
                "status": "available",
                "notes": "Synthetic map and route overlay source.",
                "updated_at": now,
            },
            {
                "id": "adapter-network-plan",
                "name": "Network Plan File Stub",
                "adapter_type": "file",
                "target_module": "jinx-net",
                "permission": "mock_adapter:read",
                "data_mode": DataMode.SYNTHETIC.value,
                "safety_classification": SafetyClassification.MOCK_ADAPTER.value,
                "supports_simulation": True,
                "explicitly_authorized": False,
                "enabled": False,
                "status": "available",
                "notes": "Synthetic network plan ingest path.",
                "updated_at": now,
            },
            {
                "id": "adapter-intel-summary",
                "name": "INTEL Summary Stub",
                "adapter_type": "intel_stub",
                "target_module": "jinx-intel",
                "permission": "mock_adapter:read",
                "data_mode": DataMode.SYNTHETIC.value,
                "safety_classification": SafetyClassification.MOCK_ADAPTER.value,
                "supports_simulation": True,
                "explicitly_authorized": False,
                "enabled": False,
                "status": "available",
                "notes": "Synthetic intelligence summary adapter.",
                "updated_at": now,
            },
            {
                "id": "adapter-file-core",
                "name": "Controlled File Ingest",
                "adapter_type": "file",
                "target_module": "jinx-core",
                "permission": "audit:write",
                "data_mode": DataMode.AUTHORIZED.value,
                "safety_classification": SafetyClassification.MOCK_ADAPTER.value,
                "supports_simulation": True,
                "explicitly_authorized": False,
                "enabled": False,
                "status": "available",
                "notes": "Authorized file ingest placeholder with audit logging.",
                "updated_at": now,
            },
            {
                "id": "adapter-message-integrator",
                "name": "Message Integrator Stub",
                "adapter_type": "message_gateway",
                "target_module": "jinx-integrator",
                "permission": "mock_adapter:read",
                "data_mode": DataMode.SYNTHETIC.value,
                "safety_classification": SafetyClassification.MOCK_ADAPTER.value,
                "supports_simulation": True,
                "explicitly_authorized": False,
                "enabled": False,
                "status": "available",
                "notes": "Synthetic message-family intake path for JINX-Integrator.",
                "updated_at": now,
            },
            {
                "id": "adapter-radio-bridge",
                "name": "Radio Bridge Controlled Plugin",
                "adapter_type": "radio_stub",
                "target_module": "jinx-core",
                "permission": "policy:evaluate",
                "data_mode": DataMode.LIVE_CONTROLLED_ADAPTER.value,
                "safety_classification": SafetyClassification.CONTROLLED_REAL_ADAPTER.value,
                "supports_simulation": True,
                "explicitly_authorized": False,
                "enabled": False,
                "status": "blocked",
                "notes": "Disabled by default; requires explicit authorization and controlled plugin review.",
                "updated_at": now,
            },
            {
                "id": "adapter-isr-live-gateway",
                "name": "ISR Live Gateway Stub",
                "adapter_type": "api",
                "target_module": "jinx-core",
                "permission": "policy:evaluate",
                "data_mode": DataMode.LIVE_CONTROLLED_ADAPTER.value,
                "safety_classification": SafetyClassification.CONTROLLED_REAL_ADAPTER.value,
                "supports_simulation": True,
                "explicitly_authorized": False,
                "enabled": False,
                "status": "blocked",
                "notes": "Controlled adapter placeholder only; real integrations remain disabled.",
                "updated_at": now,
            },
        )

    def _identity_user_by_username(self, username: str) -> dict[str, object]:
        if self.database is None:
            raise KeyError(f"user not found: {username}")
        for document in self.database.list_documents("identity_users"):
            if document.get("username") == username:
                return document
        raise KeyError(f"user not found: {username}")

    def _permissions_for_roles(self, roles: tuple[str, ...]) -> frozenset[str]:
        permissions: set[str] = set()
        for role in roles:
            role_document = self.access_control.roles.get(role)
            if role_document is not None:
                permissions.update(role_document.permissions)
        return frozenset(permissions)

    def _package_license_for(self, package: str) -> dict[str, object]:
        if self.database is None:
            return {
                "package": package,
                "active": False,
                "authorized_users": [],
                "simulation_only": True,
                "controlled_real_adapters_enabled": False,
            }
        try:
            return self.database.get_document("package_licenses", package)
        except KeyError:
            return {
                "package": package,
                "active": False,
                "authorized_users": [],
                "simulation_only": True,
                "controlled_real_adapters_enabled": False,
            }

    def package_license_allows(self, package: str, username: str = "") -> bool:
        self._ensure_governance_state()
        document = self._package_license_for(package)
        if not document.get("active", False):
            return False
        allowed_users = set(str(item) for item in document.get("authorized_users", ()))
        if not username:
            return True
        return "*" in allowed_users or username in allowed_users

    def _boundary_policy_for_package(self, package: str) -> dict[str, object]:
        policy_map = {
            "full": {
                "denied_permission_prefixes": (),
                "summary": "Full package receives all licensed advisory surfaces.",
            },
            "c5isr": {
                "denied_permission_prefixes": ("net:", "intel:", "isr:", "ops:"),
                "summary": "C5ISR package hides NET and INTEL domains outside approved abstractions.",
            },
            "net": {
                "denied_permission_prefixes": ("operator_report:", "cop:", "mission:", "intel:", "isr:", "human_command:", "ops:"),
                "summary": "NET package sees communications-domain workflows only.",
            },
            "intel": {
                "denied_permission_prefixes": ("operator_report:", "cop:", "mission:", "net:", "human_command:", "ops:"),
                "summary": "INTEL package exposes contextualization without COP or NET management surfaces.",
            },
            "integrator": {
                "denied_permission_prefixes": ("operator_report:", "cop:", "mission:", "intel:", "isr:", "net:", "human_command:", "ops:", "audit:", "sim:"),
                "summary": "Integrator package exposes bounded message intake and internal routing review only.",
            },
            "sim": {
                "denied_permission_prefixes": ("operator_report:", "cop:", "mission:", "intel:", "isr:", "net:", "human_command:", "ops:"),
                "summary": "SIM package keeps replay control separate from operational surfaces.",
            },
            "operator": {
                "denied_permission_prefixes": ("cop:", "mission:", "intel:", "isr:", "net:", "ops:", "audit:", "human_command:", "operator_report:review", "sim:"),
                "summary": "Operator Mini receives a compact local COP and advisory lane only.",
            },
        }
        return policy_map.get(package, {"denied_permission_prefixes": (), "summary": "No package boundary policy defined."})

    def _adapter_document(self, adapter_id: str) -> dict[str, object]:
        if self.database is None:
            raise KeyError(f"adapter not found: {adapter_id}")
        return self.database.get_document("adapter_manifests", adapter_id)

    def _evaluated_adapter_document(self, document: dict[str, object]) -> dict[str, object]:
        manifest = AdapterManifest(
            name=str(document["name"]),
            permission=str(document["permission"]),
            data_mode=DataMode(str(document["data_mode"])),
            safety_classification=SafetyClassification(str(document["safety_classification"])),
            supports_simulation=bool(document.get("supports_simulation", True)),
            explicitly_authorized=bool(document.get("explicitly_authorized", False)),
        )
        gate_allowed = self.adapter_gate.may_activate(manifest)
        policy = self.router._policy_engine.may_use_adapter(
            module_name=str(document["target_module"]),
            adapter_permission=str(document["permission"]),
            data_mode=manifest.data_mode,
        )
        evaluated = dict(document)
        evaluated["gate_allowed"] = gate_allowed
        evaluated["policy_allowed"] = policy.allowed
        evaluated["policy_reason"] = policy.reason
        if not evaluated.get("enabled", False):
            evaluated["status"] = "available" if gate_allowed and policy.allowed else "blocked"
        else:
            evaluated["status"] = "enabled" if gate_allowed and policy.allowed else "blocked"
            if not gate_allowed or not policy.allowed:
                evaluated["enabled"] = False
        evaluated["updated_at"] = datetime.now(UTC).isoformat()
        return evaluated

    @staticmethod
    def _brain_context_document(context: BoundedBrainContext) -> dict[str, object]:
        return {
            "id": context.id,
            "source": context.source,
            "allowed_modules": sorted(context.allowed_modules),
            "context": dict(context.context),
            "redactions": list(context.redactions),
            "uncertainty": list(context.uncertainty),
            "provenance_refs": list(context.provenance_refs),
            "timestamp": context.timestamp.isoformat(),
        }

    def _sync_audit_ledger(self) -> None:
        if self.database is None:
            return
        for record in self.audit_log.records():
            document = {
                "id": record.id,
                "event_type": record.event_type.value,
                "actor": record.actor,
                "summary": record.summary,
                "metadata": dict(record.metadata),
                "timestamp": record.timestamp.isoformat(),
            }
            self.database.save_document("audit_records", record.id, document)
            if record.event_type.value == "policy_decision":
                self.database.save_document(
                    "policy_decisions",
                    record.id,
                    {
                        **document,
                        "allowed": str(record.metadata.get("allowed", "False")).lower() == "true",
                        "source_module": record.metadata.get("source_module", ""),
                        "destination": record.metadata.get("destination", ""),
                        "payload_schema": record.metadata.get("payload_schema", ""),
                        "message_id": record.metadata.get("message_id", ""),
                    },
                )

    def _sync_fabric_ledger(self) -> None:
        if self.database is None:
            return
        for record in self.router.route_records():
            document = record.to_document()
            self.database.save_document("fabric_messages", document["message_id"], document)
            if document["status"] == "denied":
                self.database.save_document("fabric_dead_letters", document["message_id"], document)

    def _sync_provenance_ledger(self) -> None:
        if self.database is None:
            return
        for event in self._events:
            record = event.provenance
            document_id = f"prov-{event.id}"
            self.database.save_document(
                "provenance_records",
                document_id,
                {
                    "id": document_id,
                    "source": record.source,
                    "processed_by_module": record.processed_by_module,
                    "transformations": list(record.transformations),
                    "confidence": record.confidence.value,
                    "time_received": record.time_received.isoformat(),
                    "event_id": event.id,
                    "linked_object_type": "event",
                    "linked_object_id": event.id,
                },
            )

    def _persist_provenance_chain(
        self,
        linked_object_type: str,
        linked_object_id: str,
        records,
    ) -> None:
        if self.database is None:
            return
        for index, record in enumerate(records, start=1):
            document_id = f"prov-{linked_object_type}-{linked_object_id}-{index}"
            self.database.save_document(
                "provenance_records",
                document_id,
                {
                    "id": document_id,
                    "source": record.source,
                    "processed_by_module": record.processed_by_module,
                    "transformations": list(record.transformations),
                    "confidence": record.confidence.value,
                    "time_received": record.time_received.isoformat(),
                    "linked_object_type": linked_object_type,
                    "linked_object_id": linked_object_id,
                },
            )

    def _refresh_operator_loop(self, reason: str, related_ids: dict[str, str]) -> dict[str, object]:
        packet = self._build_operator_loop_packet(reason, related_ids)
        if self.database is not None:
            self.database.save_document("operator_loop_packets", "active", packet)
        return packet

    def _build_operator_loop_packet(self, reason: str, related_ids: dict[str, str]) -> dict[str, object]:
        if self.database is None:
            return {
                "id": "operator-loop-memory",
                "reason": reason,
                "status": "memory_only",
                "flow_steps": [],
                "allowed_next_steps": [],
                "disallowed_actions": [],
            }
        reports = self.database.list_documents("operator_reports")
        events = self.database.list_documents("events")
        advisories = self.database.list_documents("cop_advisories")
        conflicts = self.database.list_documents("conflicts")
        recommendations = self.database.list_documents("recommendations")
        impacts = self.database.list_documents("mission_impacts")
        intel = self.database.list_documents("intelligence_summaries")
        isr = self.database.list_documents("isr_feeds")
        net_plans = self.database.list_documents("network_plans")
        net_issues = self.database.list_documents("network_issues")
        analysis_runs = self.database.list_documents("analysis_runs")
        brain_messages = self.database.list_documents("brain_chat_messages")
        review_items = self.review_center_document()["items"]
        open_reviews = [
            item for item in review_items if item.get("review_state") not in {"validated", "closed"}
        ]
        status = "human_review_required" if open_reviews or conflicts or impacts else "monitoring"
        latest_brain = brain_messages[-1] if brain_messages else None
        return {
            "id": "operator-loop-active",
            "reason": reason,
            "related_ids": related_ids,
            "status": status,
            "summary": (
                "Operator Mini feeds C5ISR; Core analyzes conflicts and impacts; BRAIN supplies references; "
                "humans retain decision authority."
            ),
            "flow_steps": [
                self._loop_step("operator_mini", "Operator Mini intake", len(reports), reports[-1]["id"] if reports else None),
                self._loop_step("c5isr", "C5ISR event/advisory generation", len(events) + len(advisories), events[-1]["id"] if events else None),
                self._loop_step("intel_isr", "INTEL/ISR context", len(intel) + len(isr), isr[-1]["id"] if isr else (intel[-1]["id"] if intel else None)),
                self._loop_step("net", "JINX-NET validation", len(net_plans) + len(net_issues), net_issues[-1]["id"] if net_issues else (net_plans[-1]["id"] if net_plans else None)),
                self._loop_step("core", "Core analysis and conflict detection", len(analysis_runs), analysis_runs[-1]["id"] if analysis_runs else None),
                self._loop_step("brain", "BRAIN doctrine/SOP reference", len(brain_messages), latest_brain["answer"]["id"] if latest_brain else None),
                self._loop_step("human_review", "Human review queue", len(open_reviews), open_reviews[-1]["id"] if open_reviews else None),
            ],
            "latest_report_id": reports[-1]["id"] if reports else None,
            "latest_event_id": events[-1]["id"] if events else None,
            "latest_conflict_id": conflicts[-1]["id"] if conflicts else None,
            "latest_recommendation_id": recommendations[-1]["id"] if recommendations else None,
            "latest_mission_impact_id": impacts[-1]["id"] if impacts else None,
            "latest_brain_answer_id": latest_brain["answer"]["id"] if latest_brain else None,
            "open_review_count": len(open_reviews),
            "confidence_band": self._loop_confidence_band(conflicts, impacts, recommendations),
            "allowed_next_steps": [
                "Review linked reports, conflicts, recommendations, and mission impacts.",
                "Ask JINX-BRAIN for doctrine/SOP references with Core reachback enabled.",
                "Validate or close review items only through a human reviewer.",
            ],
            "disallowed_actions": [
                "Do not treat JINX output as an operational order.",
                "Do not use JINX to authorize targeting, weapons effects, or autonomous action.",
                "Do not retask ISR or modify live systems from this advisory packet.",
            ],
            "timestamp": datetime.now(UTC).isoformat(),
        }

    @staticmethod
    def _loop_step(name: str, label: str, count: int, latest_id: str | None) -> dict[str, object]:
        return {
            "name": name,
            "label": label,
            "count": count,
            "latest_id": latest_id,
            "state": "active" if count else "waiting",
        }

    @staticmethod
    def _loop_confidence_band(
        conflicts: tuple[dict[str, object], ...],
        impacts: tuple[dict[str, object], ...],
        recommendations: tuple[dict[str, object], ...],
    ) -> str:
        values = [
            float(item.get("confidence", 0.0))
            for collection in (conflicts, impacts, recommendations)
            for item in collection
        ]
        if not values:
            return "unknown"
        average = sum(values) / len(values)
        if average >= 0.75:
            return "high"
        if average >= 0.5:
            return "medium"
        return "low"

    @staticmethod
    def _find_scenario_pack(scenario_id: str) -> C5ISRScenarioPack:
        packs = default_c5isr_scenario_packs()
        for pack in packs:
            if pack.id == scenario_id or pack.name == scenario_id:
                return pack
        if scenario_id in {"", "default"}:
            return packs[0]
        raise ValueError(f"unknown scenario pack: {scenario_id}")

    @staticmethod
    def _simulation_scenario_document_from_pack(pack: C5ISRScenarioPack) -> dict[str, object]:
        injects = []
        for index, inject in enumerate(pack.injects):
            injects.append({"offset_seconds": index * 60, **inject})
        return {
            "id": pack.id,
            "name": pack.name,
            "summary": pack.summary,
            "source": "built_in",
            "scenario_type": "c5isr_pack",
            "injects": injects,
            "expected_outputs": list(pack.expected_outputs),
            "synthetic": True,
            "duration_seconds": max((inject["offset_seconds"] for inject in injects), default=0),
            "created_at": datetime.now(UTC).isoformat(),
        }

    def _load_simulation_scenario_document(self, scenario_id: str) -> dict[str, object]:
        library = self.simulation_library_document()["simulation_scenarios"]
        for scenario in library:
            if scenario["id"] == scenario_id or scenario["name"] == scenario_id:
                return scenario
        if library:
            return library[0]
        raise ValueError(f"unknown simulation scenario: {scenario_id}")

    def _run_simulation_document(self, scenario: dict[str, object]) -> dict[str, object]:
        if self.database is None:
            raise ValueError("database is required for scenario runs")
        before = self._collection_counts()
        previous_confidence = self._latest_analysis_confidence_value()
        handler = self._api_handler()
        injects = list(scenario.get("injects", []))
        if not any(inject.get("type") == "mission_context" for inject in injects):
            handler.submit_mission_context(
                {
                    "mission_statement": f"Synthetic scenario run: {scenario['name']}.",
                    "commander_intent": "Exercise advisory review paths while preserving human authority.",
                    "route": "Route Alpha",
                    "named_area": "Area Alpha",
                    "timeline": "T+00 to T+60",
                }
            )

        injected: list[dict[str, object]] = []
        for index, inject in enumerate(sorted(injects, key=lambda item: int(item.get("offset_seconds", 0))), start=1):
            injected.append(self._apply_simulation_inject(scenario, inject, index))

        brain_question = (
            f"Given the synthetic scenario {scenario['name']}, what should the human review across C5ISR, INTEL, "
            "NET, mission impact, and simulation result outputs?"
        )
        brain_answer = self.ask_brain_chat(
            text=brain_question,
            user_id="simulation-operator",
            role="simulation_operator",
            use_core_reachback=True,
        )
        after = self._collection_counts()
        actual_outputs = self._actual_outputs_from_counts(before, after)
        expected_outputs = list(scenario.get("expected_outputs", []))
        missing_outputs = [output for output in expected_outputs if output not in actual_outputs]
        unexpected_outputs = [output for output in actual_outputs if output not in expected_outputs]
        latest_confidence = self._latest_analysis_confidence_value()
        confidence_drift = 0.0
        if previous_confidence is not None and latest_confidence is not None:
            confidence_drift = round(latest_confidence - previous_confidence, 3)
        run_id = f"sim-run-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
        result_state = "matched"
        if missing_outputs and unexpected_outputs:
            result_state = "mismatch"
        elif missing_outputs or unexpected_outputs:
            result_state = "partial"
        run = {
            "id": run_id,
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "scenario_source": scenario.get("source", "built_in"),
            "scenario_type": scenario.get("scenario_type", "mixed_inject"),
            "injected": injected,
            "timeline": [
                {
                    "offset_seconds": int(inject.get("offset_seconds", 0)),
                    "type": inject.get("type", "operator_report"),
                    "summary": inject.get("summary", inject.get("name", "")),
                }
                for inject in injects
            ],
            "expected_outputs": expected_outputs,
            "actual_outputs": actual_outputs,
            "missing_outputs": missing_outputs,
            "unexpected_outputs": unexpected_outputs,
            "brain_answer_id": brain_answer["answer"]["id"],
            "status": "human_review_required",
            "result_state": result_state,
            "confidence_drift": confidence_drift,
            "clock_total_seconds": int(scenario.get("duration_seconds", 0)),
            "synthetic": True,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self.database.save_document("simulation_runs", run_id, run)
        self._save_simulation_control(
            self._control_state_for_scenario(
                scenario,
                playback_state="completed",
                action="play",
                offset_seconds=int(scenario.get("duration_seconds", 0)),
                latest_run_id=run_id,
            )
        )
        self._append_timeline(
            "simulation_run",
            f"Scenario {scenario['name']} replayed for simulation-center review.",
            {"simulation_run_id": run_id, "scenario_id": scenario["id"]},
        )
        self._refresh_operator_loop("simulation_run", {"simulation_run_id": run_id})
        return {"simulation_run": run}

    def _apply_simulation_inject(
        self,
        scenario: dict[str, object],
        inject: dict[str, Any],
        index: int,
    ) -> dict[str, object]:
        inject_type = inject.get("type", "operator_report")
        if inject_type == "operator_report":
            handler = self._api_handler()
            return handler.submit_operator_report(
                {
                    "reporter_id": inject.get("reporter_id", "operator-alpha"),
                    "device_id": inject.get("device_id", "operator-mini-sim"),
                    "report_type": inject.get("report_type", "observation"),
                    "summary": inject.get("summary", f"Synthetic scenario report {index}: {scenario['name']}."),
                    "location": inject.get("location", "Route Alpha"),
                }
            )
        if inject_type == "intel_summary":
            handler = self._api_handler()
            return handler.submit_intelligence_summary(
                {
                    "source_category": "synthetic_scenario_summary",
                    "summary": inject.get("summary", f"Synthetic scenario INTEL context for {scenario['name']}."),
                    "reliability": inject.get("reliability", "0.7"),
                    "related_locations": inject.get("related_locations", "Route Alpha,Area Alpha"),
                    "related_entities": inject.get("related_entities", "operator-alpha"),
                }
            )
        if inject_type == "isr_feed":
            handler = self._api_handler()
            return handler.submit_isr_feed_snapshot(
                {
                    "feed_name": inject.get("feed_name", "Synthetic ISR Orbit"),
                    "feed_type": inject.get("feed_type", "synthetic_full_motion_video"),
                    "status": inject.get("status", "available"),
                    "coverage_area": inject.get("coverage_area", "Route Alpha"),
                    "summary": inject.get("summary", f"Synthetic ISR feed for {scenario['name']}."),
                    "related_locations": inject.get("related_locations", "Route Alpha"),
                    "related_entities": inject.get("related_entities", "operator-alpha"),
                }
            )
        if inject_type == "network_plan":
            handler = self._api_handler()
            return handler.submit_network_plan(
                {
                    "name": inject.get("name", f"Synthetic Network Plan {index}"),
                    "node_ids": inject.get("node_ids", "node-alpha,node-bravo,node-charlie"),
                    "timeslots": inject.get(
                        "timeslots",
                        "slot-01:node-alpha,slot-01:node-bravo,slot-02:node-charlie",
                    ),
                    "los_links": inject.get("los_links", "node-alpha>node-bravo"),
                    "los_status": inject.get("los_status", "degraded"),
                    "los_rationale": inject.get(
                        "los_rationale",
                        "Synthetic terrain and relay assumptions require network review.",
                    ),
                }
            )
        if inject_type == "mission_context":
            handler = self._api_handler()
            return handler.submit_mission_context(
                {
                    "mission_statement": inject.get("mission_statement", f"Synthetic mission for {scenario['name']}."),
                    "commander_intent": inject.get(
                        "commander_intent",
                        "Exercise simulation review without changing human authority boundaries.",
                    ),
                    "route": inject.get("route", "Route Alpha"),
                    "named_area": inject.get("named_area", "Area Alpha"),
                    "timeline": inject.get("timeline", "T+00 to T+60"),
                }
            )
        raise ValueError(f"unsupported scenario inject type: {inject_type}")

    @staticmethod
    def _parse_simulation_inject_script(script: str) -> list[dict[str, Any]]:
        injects: list[dict[str, Any]] = []
        for line_number, raw_line in enumerate(script.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split("|") if part.strip()]
            if len(parts) < 2:
                raise ValueError(f"invalid simulation inject line {line_number}: {raw_line}")
            try:
                offset_seconds = int(parts[0])
            except ValueError as exc:
                raise ValueError(f"invalid inject offset on line {line_number}: {parts[0]}") from exc
            inject: dict[str, Any] = {"offset_seconds": offset_seconds, "type": parts[1]}
            for segment in parts[2:]:
                key, separator, value = segment.partition("=")
                if not separator:
                    raise ValueError(f"invalid inject field on line {line_number}: {segment}")
                inject[key.strip()] = value.strip()
            injects.append(inject)
        if not injects:
            raise ValueError("simulation scenario requires at least one inject")
        injects.sort(key=lambda item: int(item["offset_seconds"]))
        return injects

    def _control_state_for_scenario(
        self,
        scenario: dict[str, Any],
        playback_state: str,
        action: str,
        offset_seconds: int = 0,
        latest_run_id: str | None = None,
    ) -> dict[str, Any]:
        injects = list(scenario.get("injects", []))
        current_frame = self._frame_for_offset(injects, offset_seconds)
        next_frame = self._next_frame_after_offset(injects, offset_seconds)
        return {
            "id": "simulation-control-active",
            "selected_scenario_id": scenario["id"],
            "selected_scenario_name": scenario["name"],
            "selected_scenario_source": scenario.get("source", "built_in"),
            "playback_state": playback_state,
            "current_offset_seconds": offset_seconds,
            "duration_seconds": int(scenario.get("duration_seconds", 0)),
            "current_frame": current_frame,
            "next_frame": next_frame,
            "latest_run_id": latest_run_id,
            "last_action": action,
            "updated_at": datetime.now(UTC).isoformat(),
        }

    def _save_simulation_control(self, control: dict[str, Any]) -> dict[str, Any]:
        if self.database is not None:
            self.database.save_document("simulation_control", "active", control)
        return control

    def _default_simulation_control(self) -> dict[str, Any]:
        scenario = self.simulation_library_document()["simulation_scenarios"][0]
        return self._control_state_for_scenario(scenario, playback_state="idle", action="bootstrap")

    @staticmethod
    def _frame_for_offset(injects: list[dict[str, Any]], offset_seconds: int) -> dict[str, Any] | None:
        current = None
        for inject in injects:
            if int(inject.get("offset_seconds", 0)) <= offset_seconds:
                current = inject
        if current is None:
            return None
        return {
            "offset_seconds": int(current.get("offset_seconds", 0)),
            "type": current.get("type", "operator_report"),
            "summary": current.get(
                "summary",
                current.get(
                    "name",
                    current.get(
                        "mission_statement",
                        current.get("feed_name", current.get("report_type", "")),
                    ),
                ),
            ),
        }

    @staticmethod
    def _next_frame_after_offset(injects: list[dict[str, Any]], offset_seconds: int) -> dict[str, Any] | None:
        for inject in injects:
            if int(inject.get("offset_seconds", 0)) > offset_seconds:
                return {
                    "offset_seconds": int(inject.get("offset_seconds", 0)),
                    "type": inject.get("type", "operator_report"),
                    "summary": inject.get(
                        "summary",
                        inject.get(
                            "name",
                            inject.get(
                                "mission_statement",
                                inject.get("feed_name", inject.get("report_type", "")),
                            ),
                        ),
                    ),
                }
        return None

    def _next_simulation_offset(self, scenario: dict[str, Any], current_offset: int) -> int:
        injects = list(scenario.get("injects", []))
        next_frame = self._next_frame_after_offset(injects, current_offset)
        if next_frame is None:
            return int(scenario.get("duration_seconds", current_offset))
        return int(next_frame["offset_seconds"])

    def _api_handler(self):
        from jinx.api import JINXAPIHandlers

        return JINXAPIHandlers(self)

    def _collection_counts(self) -> dict[str, int]:
        if self.database is None:
            return {}
        return {
            collection: self.database.count(collection)
            for collection in (
                "operator_reports",
                "events",
                "conflicts",
                "recommendations",
                "mission_impacts",
                "mission_contexts",
                "brain_chat_messages",
                "analysis_runs",
                "integrator_messages",
                "intelligence_summaries",
                "isr_feeds",
                "network_plans",
            )
        }

    @staticmethod
    def _actual_outputs_from_counts(before: dict[str, int], after: dict[str, int]) -> list[str]:
        labels = {
            "operator_reports": "operator_report_intake",
            "events": "c5isr_event_generation",
            "conflicts": "core_conflict_packet",
            "recommendations": "human_review_path",
            "mission_impacts": "mission_impact_packet",
            "mission_contexts": "mission_context_update",
            "brain_chat_messages": "brain_reference_answer",
            "analysis_runs": "core_analysis",
            "integrator_messages": "message_intake_routed",
            "intelligence_summaries": "intel_summary_ingest",
            "isr_feeds": "isr_feed_publish",
            "network_plans": "network_plan_validation",
        }
        outputs = [
            label
            for collection, label in labels.items()
            if after.get(collection, 0) > before.get(collection, 0)
        ]
        return outputs or ["no_new_outputs"]

    def _latest_analysis_confidence_value(self) -> float | None:
        if self.database is None:
            return None
        runs = self.database.list_documents("analysis_runs")
        if not runs:
            return None
        latest = runs[-1].get("confidence_summary", {})
        try:
            return float(latest.get("value"))
        except (TypeError, ValueError):
            return None

    def _event_from_network_issue(self, issue: NetworkIssue, plan: NetworkPlan) -> Event:
        event_type = EventType.COMMUNICATIONS_LOSS if issue.severity == "high" else EventType.COMMUNICATIONS_CHECK
        provenance = ProvenanceRecord(
            source=issue.id,
            time_received=datetime.now(UTC),
            processed_by_module="jinx-c5isr",
            transformations=("network_issue_received", "event_normalized"),
            confidence=issue.confidence,
            downstream_outputs=(plan.id, issue.id),
        )
        return Event(
            event_type=event_type,
            source="jinx-net",
            description=issue.summary,
            confidence=issue.confidence,
            provenance=provenance,
            data_mode=plan.data_mode,
            location=Location(label="network-domain"),
            metadata={
                "input_source": "jinx-net",
                "network_plan_id": plan.id,
                "network_issue_id": issue.id,
                "issue_type": issue.issue_type,
                "severity": issue.severity,
                "communications_status": "unavailable" if issue.severity == "high" else "available",
                "mission_impact_tags": "communications,network",
            },
            simulation_flag=plan.simulation_flag,
        )

    def _event_from_integrator_message(self, parse_result: IntegratorParseResult) -> Event:
        intake = parse_result.intake
        lowered = f"{intake.message_type} {intake.summary}".lower()
        if any(term in lowered for term in ("weather", "visibility")):
            event_type = EventType.WEATHER_IMPACT
        elif any(term in lowered for term in ("delay", "movement")):
            event_type = EventType.MOVEMENT_DELAY
        elif any(term in lowered for term in ("hazard", "threat", "contact")):
            event_type = EventType.HAZARD
        elif intake.message_family in {"j-series", "k-series"}:
            event_type = EventType.COMMUNICATIONS_CHECK
        elif "position" in lowered or parse_result.extracted_fields.get("location"):
            event_type = EventType.POSITION_UPDATE
        else:
            event_type = EventType.STATUS_UPDATE

        location_label = parse_result.extracted_fields.get("location", "")
        provenance = ProvenanceRecord(
            source=intake.id,
            time_received=datetime.now(UTC),
            processed_by_module="jinx-integrator",
            transformations=("message_family_parsed", "bounded_intake_normalized", "event_normalized"),
            confidence=intake.confidence,
            downstream_outputs=(intake.id,),
        )
        return Event(
            event_type=event_type,
            source=f"jinx-integrator:{intake.message_family}",
            description=intake.summary,
            confidence=intake.confidence,
            provenance=provenance,
            data_mode=intake.data_mode,
            location=Location(label=location_label) if location_label else None,
            metadata={
                "input_source": "jinx-integrator",
                "integrator_message_id": intake.id,
                "message_family": intake.message_family,
                "message_type": intake.message_type,
                "originator": intake.originator,
                "recipient": intake.recipient,
                "transport": intake.transport,
                "network_scope": intake.network_scope,
                "filter_profile": intake.filter_profile,
                "mission_impact_tags": ",".join(intake.tags),
            },
            simulation_flag=intake.simulation_flag,
        )

    def _persist_network_plan(
        self,
        plan: NetworkPlan,
        validation_run: NetworkValidationRun,
        issues: tuple[NetworkIssue, ...],
        routes: tuple[RouteResult, ...],
        events: tuple[Event, ...],
    ) -> None:
        if self.database is None:
            return
        self.database.save_document(
            "network_plans",
            plan.id,
            {
                "id": plan.id,
                "name": plan.name,
                "source_format": plan.source_format,
                "nodes": [
                    {"id": node.id, "label": node.label, "node_type": node.node_type}
                    for node in plan.nodes
                ],
                "timeslots": [
                    {
                        "slot_id": allocation.slot_id,
                        "node_id": allocation.node_id,
                        "epoch": allocation.epoch,
                        "purpose": allocation.purpose,
                    }
                    for allocation in plan.timeslots
                ],
                "los_links": [
                    {
                        "from_node": link.from_node,
                        "to_node": link.to_node,
                        "status": link.status,
                        "rationale": link.rationale,
                    }
                    for link in plan.los_links
                ],
                "confidence": plan.confidence.value,
                "data_mode": plan.data_mode.value,
                "simulation_flag": plan.simulation_flag,
                "timestamp": plan.timestamp.isoformat(),
            },
        )
        self.database.save_document(
            "network_validation_runs",
            validation_run.id,
            {
                "id": validation_run.id,
                "plan_id": validation_run.plan_id,
                "issue_ids": list(validation_run.issue_ids),
                "confidence": validation_run.confidence.value,
                "summary": validation_run.summary,
                "timestamp": validation_run.timestamp.isoformat(),
            },
        )
        delivered_by_issue = {route.message.provenance_ref: route.delivered for route in routes}
        for issue in issues:
            self.database.save_document(
                "network_issues",
                issue.id,
                {
                    "id": issue.id,
                    "plan_id": plan.id,
                    "issue_type": issue.issue_type,
                    "summary": issue.summary,
                    "affected_nodes": list(issue.affected_nodes),
                    "confidence": issue.confidence.value,
                    "recommended_review_role": issue.recommended_review_role,
                    "severity": issue.severity,
                    "recommended_human_actions": list(issue.recommended_human_actions),
                    "disallowed_actions": list(issue.disallowed_actions),
                    "delivered_to_core": delivered_by_issue.get(issue.id, False),
                    "timestamp": issue.timestamp.isoformat(),
                },
            )
            self.database.save_document(
                "network_advisories",
                f"net-advisory-{issue.id}",
                {
                    "id": f"net-advisory-{issue.id}",
                    "issue_id": issue.id,
                    "plan_id": plan.id,
                    "summary": f"JINX-NET advisory: {issue.summary}",
                    "required_human_review": True,
                    "recommended_review_role": issue.recommended_review_role,
                    "allowed_actions": list(issue.recommended_human_actions),
                    "disallowed_actions": list(issue.disallowed_actions),
                    "confidence": issue.confidence.value,
                },
            )
            self._persist_provenance_chain("network_issue", issue.id, (issue.provenance,))
            self._save_evidence_pack(
                source_kind="network_issue",
                source_id=issue.id,
                source_module="jinx-net",
                package_scope="net",
                title=f"NET issue {issue.issue_type}",
                summary=issue.summary,
                confidence_value=issue.confidence.value,
                recommended_review_role=issue.recommended_review_role,
                related_ids=(plan.id, validation_run.id, f"net-advisory-{issue.id}"),
                provenance_refs=(issue.id,),
                assumptions=("Network validation remains synthetic and advisory only.",),
                uncertainty=("Network-domain timing and LOS assumptions may change with scenario inputs.",),
                allowed_actions=tuple(issue.recommended_human_actions),
                disallowed_actions=tuple(issue.disallowed_actions),
                tags=("net", "issue", issue.severity, issue.issue_type),
                simulation_flag=plan.simulation_flag,
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
                    "network_plan_id": event.metadata.get("network_plan_id"),
                    "network_issue_id": event.metadata.get("network_issue_id"),
                    "mission_impact_tags": event.metadata.get("mission_impact_tags", ""),
                "timestamp": event.timestamp.isoformat(),
            },
        )

    def _persist_integrator_message(
        self,
        parse_result: IntegratorParseResult,
        routes: tuple[RouteResult, ...],
        event: Event,
    ) -> None:
        if self.database is None:
            return
        intake = parse_result.intake
        parse_run_id = f"integrator-parse-{intake.id}"
        self.database.save_document(
            "integrator_messages",
            intake.id,
            {
                "id": intake.id,
                "message_family": intake.message_family,
                "message_type": intake.message_type,
                "originator": intake.originator,
                "recipient": intake.recipient,
                "summary": intake.summary,
                "raw_text": intake.raw_text,
                "transport": intake.transport,
                "precedence": intake.precedence,
                "network_scope": intake.network_scope,
                "filter_profile": intake.filter_profile,
                "route_targets": list(intake.route_targets),
                "restrictions": list(intake.restrictions),
                "tags": list(intake.tags),
                "confidence": intake.confidence.value,
                "data_mode": intake.data_mode.value,
                "simulation_flag": intake.simulation_flag,
                "validation_notes": list(parse_result.validation_notes),
                "filter_actions": list(parse_result.filter_actions),
                "extracted_fields": dict(parse_result.extracted_fields),
                "authority_state": "observed_external_message_only",
                "parse_run_id": parse_run_id,
                "event_id": event.id,
                "timestamp": intake.timestamp.isoformat(),
            },
        )
        self.database.save_document(
            "integrator_parser_runs",
            parse_run_id,
            {
                "id": parse_run_id,
                "message_id": intake.id,
                "message_family": intake.message_family,
                "normalized_payload": dict(parse_result.normalized_payload),
                "normalized_keys": sorted(str(key) for key in parse_result.normalized_payload.keys()),
                "validation_notes": list(parse_result.validation_notes),
                "filter_actions": list(parse_result.filter_actions),
                "route_targets": list(intake.route_targets),
                "timestamp": intake.timestamp.isoformat(),
            },
        )
        for route in routes:
            route_id = f"integrator-route-{intake.id}-{route.message.destination.replace('jinx-', '')}"
            self.database.save_document(
                "integrator_routes",
                route_id,
                {
                    "id": route_id,
                    "message_id": intake.id,
                    "destination": route.message.destination,
                    "topic": route.message.topic,
                    "status": route.status,
                    "delivered": route.delivered,
                    "policy_reason": route.decision.reason,
                    "redacted_fields": list(route.redacted_fields),
                    "payload_schema": route.message.payload_schema,
                    "simulation_flag": route.message.simulation_flag,
                    "license_scope": route.message.license_scope,
                    "timestamp": route.message.timestamp.isoformat(),
                },
            )
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
                "integrator_message_id": intake.id,
                "message_family": intake.message_family,
                "message_type": intake.message_type,
                "timestamp": event.timestamp.isoformat(),
            },
        )
        self._save_evidence_pack(
            source_kind="integrator_message",
            source_id=intake.id,
            source_module="jinx-integrator",
            package_scope="integrator",
            title=f"Integrator intake {intake.message_family}",
            summary=intake.summary,
            confidence_value=intake.confidence.value,
            recommended_review_role="integrator operator",
            related_ids=(parse_run_id, event.id, *tuple(route.message.destination for route in routes)),
            provenance_refs=(intake.id,),
            assumptions=tuple(intake.restrictions),
            uncertainty=tuple(parse_result.validation_notes),
            allowed_actions=(
                "Review bounded message intake output.",
                "Route only through licensed internal JINX modules.",
                "Use simulation replay before reusing message-derived assumptions.",
            ),
            disallowed_actions=(
                "Do not forward this intake to a live external network path.",
                "Do not convert this intake into autonomous command or tasking.",
            ),
            tags=("integrator", intake.message_family, "message_intake"),
            simulation_flag=intake.simulation_flag,
        )
        self._append_timeline(
            "integrator_message",
            f"Integrator normalized {intake.message_family} intake for bounded internal review.",
            {"message_id": intake.id, "parse_run_id": parse_run_id},
        )

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

    @staticmethod
    def _operator_quick_actions() -> list[dict[str, str]]:
        return [
            {
                "id": "position",
                "label": "Position",
                "report_type": "position_update",
                "template": "Position update from {reporter_id} near {location}.",
            },
            {
                "id": "hazard",
                "label": "Hazard",
                "report_type": "hazard",
                "template": "Hazard observed near {location}. Human review recommended.",
            },
            {
                "id": "contact",
                "label": "Contact",
                "report_type": "observation",
                "template": "Possible contact or threat activity observed near {location}. Confidence limited pending review.",
            },
            {
                "id": "delay",
                "label": "Delay",
                "report_type": "status_update",
                "template": "Movement delay reported near {location}.",
            },
            {
                "id": "comms",
                "label": "Comms",
                "report_type": "communications_check",
                "template": "Communications issue reported near {location}.",
            },
            {
                "id": "medevac",
                "label": "Medevac",
                "report_type": "medical",
                "template": "Medical event or medevac support may be required near {location}.",
            },
            {
                "id": "logistics",
                "label": "Logistics",
                "report_type": "logistics",
                "template": "Logistics support issue reported near {location}.",
            },
            {
                "id": "unknown",
                "label": "Unknown",
                "report_type": "unknown_requires_review",
                "template": "Unknown field report requiring human review near {location}.",
            },
        ]

    @staticmethod
    def _operator_map_marker(
        marker_id: str,
        label: str,
        kind: str,
        status: str,
        confidence: float,
        summary: str,
        related_id: str,
    ) -> dict[str, object]:
        seed = sum(ord(character) for character in f"{marker_id}:{label}:{kind}")
        return {
            "id": marker_id,
            "label": label,
            "kind": kind,
            "status": status,
            "confidence": round(confidence, 2),
            "summary": summary,
            "related_id": related_id,
            "left_percent": 14 + (seed % 70),
            "top_percent": 18 + ((seed * 7) % 58),
        }

    def cop_state_document(self) -> dict[str, object]:
        try:
            state = self.cop_manager.state()
        except ValueError:
            return {
                "id": "cop-empty",
                "name": "empty",
                "data_mode": DataMode.SYNTHETIC.value,
                "mission_context_id": self.mission_context.id if self.mission_context else None,
                "tracks": [],
            }
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
        self._save_evidence_pack(
            source_kind="operator_report",
            source_id=report.id,
            source_module="jinx-c5isr",
            package_scope="c5isr",
            title=f"Operator report {report.report_type.value}",
            summary=report.summary,
            confidence_value=report.confidence.value,
            recommended_review_role="c5isr manager",
            related_ids=(intake.event.id, intake.advisory.id),
            provenance_refs=(report.id,),
            assumptions=("Operator report remains human-originated and advisory only.",),
            uncertainty=("Report content requires human validation before operational use.",),
            allowed_actions=tuple(intake.advisory.allowed_actions),
            disallowed_actions=tuple(intake.advisory.disallowed_actions),
            tags=("operator", "c5isr", report.report_type.value),
            simulation_flag=report.simulation_flag,
        )
        self._append_timeline(
            "operator_report",
            f"{report.reporter_id} submitted {report.report_type.value}.",
            {"report_id": report.id, "event_id": intake.event.id},
        )
        if intake.event.location is not None:
            self.database.save_document("cop_states", "latest", self.cop_state_document())

    def _run_core_analysis(self) -> CoreReasoningResult | None:
        if not self._events:
            return None
        result = self.core_reasoning.review_events(tuple(self._events))
        self._persist_core_analysis(result)
        self._persist_mission_impacts(self._mission_impacts())
        return result

    def _persist_core_analysis(self, result: CoreReasoningResult) -> None:
        if self.database is None:
            return
        if result.analysis_run is not None:
            summary = result.analysis_run.confidence_summary
            self.database.save_document(
                "analysis_runs",
                result.analysis_run.id,
                {
                    "id": result.analysis_run.id,
                    "input_ids": list(result.analysis_run.input_ids),
                    "modules_consulted": list(result.analysis_run.modules_consulted),
                    "confidence_summary": {
                        "value": summary.value,
                        "band": summary.band,
                        "rationale": summary.rationale,
                        "source_quality": summary.source_quality,
                        "recency_factor": summary.recency_factor,
                        "corroboration_factor": summary.corroboration_factor,
                        "contradiction_factor": summary.contradiction_factor,
                        "completeness_factor": summary.completeness_factor,
                        "delta": summary.delta,
                    },
                    "output_ids": list(result.analysis_run.output_ids),
                    "human_review_required": result.analysis_run.human_review_required,
                    "timestamp": result.analysis_run.timestamp.isoformat(),
                },
            )
        for explanation in result.explanations:
            self.database.save_document(
                "explanations",
                explanation.id,
                {
                    "id": explanation.id,
                    "output_id": explanation.output_id,
                    "output_type": explanation.output_type,
                    "why_flagged": explanation.why_flagged,
                    "contributing_inputs": list(explanation.contributing_inputs),
                    "brain_references": list(explanation.brain_references),
                    "uncertainty": explanation.uncertainty,
                    "recommended_review_role": explanation.recommended_review_role,
                    "allowed_actions": list(explanation.allowed_actions),
                    "disallowed_actions": list(explanation.disallowed_actions),
                },
            )
            self._save_evidence_pack(
                source_kind="explanation",
                source_id=explanation.id,
                source_module="jinx-core",
                package_scope="full",
                title=f"Core explanation {explanation.output_type}",
                summary=explanation.why_flagged,
                confidence_value=result.analysis_run.confidence_summary.value if result.analysis_run is not None else 0.58,
                recommended_review_role=explanation.recommended_review_role,
                related_ids=(explanation.output_id, *explanation.contributing_inputs),
                provenance_refs=tuple(explanation.contributing_inputs),
                uncertainty=(explanation.uncertainty,),
                brain_references=tuple(explanation.brain_references),
                allowed_actions=tuple(explanation.allowed_actions),
                disallowed_actions=tuple(explanation.disallowed_actions),
                tags=("core", "explanation", explanation.output_type),
            )
        for conflict in result.conflicts:
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
            self._persist_provenance_chain("conflict", conflict.id, conflict.provenance_chain)
            self._save_evidence_pack(
                source_kind="conflict",
                source_id=conflict.id,
                source_module=conflict.detected_by_module,
                package_scope="c5isr",
                title=f"Conflict {conflict.conflict_type}",
                summary=conflict.explanation,
                confidence_value=conflict.confidence.value,
                recommended_review_role=conflict.recommended_review_role,
                related_ids=tuple(conflict.conflicting_items),
                provenance_refs=tuple(record.source for record in conflict.provenance_chain),
                uncertainty=tuple(conflict.likely_impacts),
                allowed_actions=tuple(conflict.potential_human_resolutions),
                disallowed_actions=("No automated conflict resolution.",),
                tags=("core", "conflict", conflict.conflict_type),
            )
        for recommendation in result.recommendations:
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
            self._persist_provenance_chain("recommendation", recommendation.id, recommendation.provenance_chain)
            self._save_evidence_pack(
                source_kind="recommendation",
                source_id=recommendation.id,
                source_module="jinx-core",
                package_scope="full",
                title=f"Recommendation {recommendation.recommendation_type}",
                summary=recommendation.text,
                confidence_value=recommendation.confidence.value,
                recommended_review_role="human reviewer",
                related_ids=tuple(recommendation.brain_references),
                provenance_refs=tuple(record.source for record in recommendation.provenance_chain),
                assumptions=tuple(recommendation.assumptions),
                uncertainty=tuple(recommendation.risks),
                brain_references=tuple(recommendation.brain_references),
                allowed_actions=tuple(recommendation.allowed_actions),
                disallowed_actions=tuple(recommendation.disallowed_actions),
                tags=("core", "recommendation", recommendation.recommendation_type),
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
        self._save_evidence_pack(
            source_kind="intelligence_summary",
            source_id=summary.id,
            source_module="jinx-intel",
            package_scope="intel",
            title=f"INTEL summary {summary.source_category}",
            summary=summary.summary,
            confidence_value=summary.confidence.value,
            recommended_review_role="intel analyst",
            related_ids=tuple(summary.related_entities + summary.related_locations),
            provenance_refs=(summary.id,),
            assumptions=tuple(summary.restrictions),
            uncertainty=("Intelligence context requires analyst review before operational use.",),
            tags=("intel", "summary", summary.source_category),
            simulation_flag=summary.simulation_flag,
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
            self._save_evidence_pack(
                source_kind="intel_impact",
                source_id=impact.id,
                source_module="jinx-intel",
                package_scope="intel",
                title=f"INTEL impact {impact.impacted_area}",
                summary=impact.summary,
                confidence_value=impact.confidence.value,
                recommended_review_role="intel analyst",
                related_ids=(summary.id,),
                provenance_refs=(impact.id,),
                assumptions=tuple(summary.restrictions),
                uncertainty=("Impact correlation remains confidence-limited and advisory only.",),
                tags=("intel", "impact", impact.impacted_area),
            )
            affected_modules = self._affected_modules_for_intel_impact(impact.impacted_area)
            correlation_id = f"intel-correlation-{summary.id}-{impact.id}"
            self.database.save_document(
                "intel_correlations",
                correlation_id,
                {
                    "id": correlation_id,
                    "intel_summary_id": summary.id,
                    "intel_impact_id": impact.id,
                    "source_category": summary.source_category,
                    "impacted_area": impact.impacted_area,
                    "summary": impact.summary,
                    "related_entities": list(summary.related_entities),
                    "related_locations": list(summary.related_locations),
                    "affected_modules": list(affected_modules),
                    "confidence": impact.confidence.value,
                    "reliability": summary.reliability,
                    "restrictions": list(summary.restrictions),
                    "recommended_review_role": "intel analyst",
                    "required_human_review": True,
                    "delivered_to_core": delivered_by_impact.get(impact.id, False),
                    "timestamp": summary.timestamp.isoformat(),
                },
            )
            for module in affected_modules:
                notice_id = f"intel-notice-{summary.id}-{impact.id}-{module}"
                self.database.save_document(
                    "intel_module_notices",
                    notice_id,
                    {
                        "id": notice_id,
                        "module": module,
                        "intel_summary_id": summary.id,
                        "intel_impact_id": impact.id,
                        "summary": f"{module} review notice: {impact.summary}",
                        "confidence": impact.confidence.value,
                        "required_human_review": True,
                        "delivered_to_core": delivered_by_impact.get(impact.id, False),
                    },
                )
                self._save_evidence_pack(
                    source_kind="intel_notice",
                    source_id=notice_id,
                    source_module="jinx-intel",
                    package_scope="intel",
                    title=f"INTEL notice for {module}",
                    summary=f"{module} review notice: {impact.summary}",
                    confidence_value=impact.confidence.value,
                    recommended_review_role="intel analyst",
                    related_ids=(summary.id, impact.id, module),
                    provenance_refs=(summary.id, impact.id),
                    assumptions=("Notice distribution remains package and boundary controlled.",),
                    uncertainty=("Receiving module may require additional human review before acting.",),
                    tags=("intel", "notice", module),
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
            self._save_evidence_pack(
                source_kind="mission_impact",
                source_id=impact.id,
                source_module="jinx-core",
                package_scope="c5isr",
                title=f"Mission impact {impact.impacted_area}",
                summary=impact.summary,
                confidence_value=impact.confidence.value,
                recommended_review_role=impact.recommended_review_role,
                related_ids=tuple(impact.source_event_ids),
                provenance_refs=tuple(record.source for record in impact.provenance_chain),
                assumptions=tuple(impact.affected_tasks),
                uncertainty=(impact.rationale,),
                tags=("mission", "impact", impact.impacted_area),
            )
            self._append_timeline(
                "mission_impact",
                impact.summary,
                {"impact_id": impact.id, "impacted_area": impact.impacted_area},
            )

    @staticmethod
    def _affected_modules_for_intel_impact(impacted_area: str) -> tuple[str, ...]:
        if impacted_area == "weather_constraints":
            return ("jinx-c5isr", "jinx-net", "jinx-sim")
        if impacted_area == "communications_assumptions":
            return ("jinx-c5isr", "jinx-net")
        return ("jinx-core", "jinx-brain")

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
