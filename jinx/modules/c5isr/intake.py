"""C5ISR intake workflow for JINX-Operator Mini reports."""

from dataclasses import dataclass
from datetime import UTC, datetime

from jinx.common.types import AdvisoryLabel, DataMode, EventType, OperatorReportType
from jinx.core.provenance import ProvenanceRecord
from jinx.core.schemas import COPAdvisory, Event, OperatorReport


@dataclass(frozen=True, slots=True)
class C5ISRIntakeResult:
    event: Event
    advisory: COPAdvisory


class C5ISRReportIntake:
    def ingest_operator_report(self, report: OperatorReport) -> C5ISRIntakeResult:
        event = self._event_from_report(report)
        advisory = self._advisory_from_report(report)
        return C5ISRIntakeResult(event=event, advisory=advisory)

    def _event_from_report(self, report: OperatorReport) -> Event:
        provenance = ProvenanceRecord(
            source=report.id,
            time_received=datetime.now(UTC),
            processed_by_module="jinx-c5isr",
            transformations=("operator_report_ingested", "event_normalized"),
            confidence=report.confidence,
            downstream_outputs=(report.id,),
        )
        return Event(
            event_type=self._event_type_for_report(report.report_type),
            source=report.source_device_id,
            description=report.summary,
            confidence=report.confidence,
            provenance=provenance,
            data_mode=report.data_mode,
            location=report.location,
            metadata={
                "operator_report_id": report.id,
                "report_type": report.report_type.value,
                "reporter_id": report.reporter_id,
            },
            simulation_flag=report.simulation_flag,
        )

    def _advisory_from_report(self, report: OperatorReport) -> COPAdvisory:
        return COPAdvisory(
            label=AdvisoryLabel.HUMAN_REVIEW_REQUIRED,
            recipient_id=report.reporter_id,
            summary="Operator report received and queued for C5ISR/Core review.",
            rationale=(
                "The report is treated as a human-originated field observation. "
                "JINX preserves uncertainty until approved review and correlation occur."
            ),
            confidence=report.confidence,
            provenance_chain=(report.provenance,),
            required_human_review=True,
            allowed_actions=(
                "Continue reporting observations as needed.",
                "Wait for human-confirmed updates through approved channels.",
            ),
            disallowed_actions=(
                "Do not treat this advisory as an operational order.",
                "Do not treat this advisory as a targeting decision.",
                "Do not modify live systems based on this advisory alone.",
            ),
            related_report_ids=(report.id,),
        )

    @staticmethod
    def _event_type_for_report(report_type: OperatorReportType) -> EventType:
        mapping = {
            OperatorReportType.COMMUNICATIONS_CHECK: EventType.COMMUNICATIONS_CHECK,
            OperatorReportType.LOGISTICS: EventType.LOGISTICS_ISSUE,
            OperatorReportType.MEDICAL: EventType.UNKNOWN_REQUIRES_REVIEW,
            OperatorReportType.HAZARD: EventType.UNKNOWN_REQUIRES_REVIEW,
            OperatorReportType.OBSERVATION: EventType.UNKNOWN_REQUIRES_REVIEW,
            OperatorReportType.POSITION_UPDATE: EventType.UNKNOWN_REQUIRES_REVIEW,
            OperatorReportType.REQUEST_INFORMATION: EventType.UNKNOWN_REQUIRES_REVIEW,
            OperatorReportType.STATUS_UPDATE: EventType.UNKNOWN_REQUIRES_REVIEW,
            OperatorReportType.UNKNOWN_REQUIRES_REVIEW: EventType.UNKNOWN_REQUIRES_REVIEW,
        }
        return mapping[report_type]
