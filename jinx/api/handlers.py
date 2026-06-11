"""Dependency-free API-style handlers for early integration tests."""

from jinx.app import JINXApplicationService
from jinx.common.types import DataMode, HumanCommandType, OperatorReportType
from jinx.modules.operator_mini import OperatorMiniClient
from jinx.core.schemas import Location
from jinx.common.types.confidence import ConfidenceScore
from jinx.core.provenance import ProvenanceRecord
from datetime import UTC, datetime


class JINXAPIHandlers:
    def __init__(self, service: JINXApplicationService | None = None) -> None:
        self.service = service or JINXApplicationService()

    def submit_operator_report(self, payload: dict[str, str]) -> dict[str, object]:
        client = OperatorMiniClient(
            reporter_id=payload["reporter_id"],
            device_id=payload["device_id"],
            data_mode=DataMode.SYNTHETIC,
        )
        report = client.create_report(
            report_type=OperatorReportType(payload.get("report_type", OperatorReportType.OBSERVATION.value)),
            summary=payload["summary"],
            confidence=self._synthetic_confidence(),
            provenance=self._synthetic_provenance("jinx-api.operator-mini"),
            location=Location(label=payload.get("location", "synthetic-unknown")),
        )
        result = self.service.submit_operator_report(report)
        return {
            "report_id": report.id,
            "event_id": result.intake.event.id,
            "advisory_id": result.intake.advisory.id,
            "delivered": result.report_route.delivered and result.advisory_route.delivered,
        }

    def submit_human_command(self, payload: dict[str, str]) -> dict[str, object]:
        client = OperatorMiniClient(
            reporter_id=payload["issuing_user_id"],
            device_id=payload["device_id"],
            data_mode=DataMode.SYNTHETIC,
        )
        command = client.create_human_command(
            command_type=HumanCommandType(payload.get("command_type", HumanCommandType.HUMAN_DIRECTION.value)),
            text=payload["text"],
            issuing_role=payload["issuing_role"],
            provenance=self._synthetic_provenance("jinx-api.human-command"),
            target_module=payload["target_module"],
        )
        result = self.service.submit_human_command(command)
        return {"command_id": command.id, "delivered": result.delivered}

    @staticmethod
    def _synthetic_confidence() -> ConfidenceScore:
        return ConfidenceScore(
            value=0.6,
            scale="0.0-1.0",
            rationale="API handler synthetic input default.",
            source_quality=0.6,
            recency_factor=0.8,
            corroboration_factor=0.2,
            contradiction_factor=0.1,
            completeness_factor=0.5,
        )

    @classmethod
    def _synthetic_provenance(cls, module: str) -> ProvenanceRecord:
        return ProvenanceRecord(
            source="jinx-api-handler",
            time_received=datetime.now(UTC),
            processed_by_module=module,
            transformations=("api_payload_normalized",),
            confidence=cls._synthetic_confidence(),
        )
