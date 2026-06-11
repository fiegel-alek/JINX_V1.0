"""High-level application orchestration services."""

from dataclasses import dataclass

from jinx.bus import FabricMessage, MessageRouter, RouteResult
from jinx.common.types import DataMode
from jinx.core.audit import AuditLog
from jinx.core.policy import PolicyEngine
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
    def __init__(self, router: MessageRouter | None = None) -> None:
        self.audit_log = AuditLog()
        self.router = router or MessageRouter(PolicyEngine(build_default_registry()), self.audit_log)
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
        return OperatorReportResult(intake=intake, report_route=report_route, advisory_route=advisory_route)

    def submit_human_command(self, command: HumanCommandInput) -> RouteResult:
        return self.router.route(
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
