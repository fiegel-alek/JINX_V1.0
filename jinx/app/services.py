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
from jinx.core.schemas import HumanCommandInput, OperatorReport
from jinx.modules.c5isr import C5ISRIntakeResult, C5ISRReportIntake, COPManager


@dataclass(frozen=True, slots=True)
class OperatorReportResult:
    intake: C5ISRIntakeResult
    report_route: RouteResult
    advisory_route: RouteResult


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
        self._persist_operator_report(report, intake, report_route, advisory_route)
        return OperatorReportResult(intake=intake, report_route=report_route, advisory_route=advisory_route)

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
