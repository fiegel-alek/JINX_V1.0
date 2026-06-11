"""Operator Mini client-side object factory."""

from jinx.common.types import DataMode, HumanCommandType, OperatorReportType
from jinx.common.types.confidence import ConfidenceScore
from jinx.core.provenance import ProvenanceRecord
from jinx.core.schemas import HumanCommandInput, Location, OperatorReport


class OperatorMiniClient:
    def __init__(self, reporter_id: str, device_id: str, data_mode: DataMode = DataMode.SYNTHETIC) -> None:
        if not reporter_id:
            raise ValueError("reporter_id is required")
        if not device_id:
            raise ValueError("device_id is required")
        self.reporter_id = reporter_id
        self.device_id = device_id
        self.data_mode = data_mode

    def create_report(
        self,
        report_type: OperatorReportType,
        summary: str,
        confidence: ConfidenceScore,
        provenance: ProvenanceRecord,
        location: Location | None = None,
    ) -> OperatorReport:
        return OperatorReport(
            report_type=report_type,
            reporter_id=self.reporter_id,
            source_device_id=self.device_id,
            summary=summary,
            confidence=confidence,
            provenance=provenance,
            data_mode=self.data_mode,
            location=location,
        )

    def create_human_command(
        self,
        command_type: HumanCommandType,
        text: str,
        issuing_role: str,
        provenance: ProvenanceRecord,
        target_module: str,
    ) -> HumanCommandInput:
        return HumanCommandInput(
            command_type=command_type,
            issuing_user_id=self.reporter_id,
            issuing_role=issuing_role,
            text=text,
            provenance=provenance,
            data_mode=self.data_mode,
            target_module=target_module,
        )
