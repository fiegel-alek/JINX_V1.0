"""C5ISR intake workflow for JINX-Operator Mini reports."""

from dataclasses import dataclass
from datetime import UTC, datetime

from jinx.common.types import AdvisoryLabel, DataMode
from jinx.core.provenance import ProvenanceRecord
from jinx.core.schemas import COPAdvisory, Event, OperatorReport
from jinx.modules.c5isr.classification import C5ISREventClassifier
from jinx.modules.intel import IntelligenceImpact


@dataclass(frozen=True, slots=True)
class C5ISRIntakeResult:
    event: Event
    advisory: COPAdvisory


class C5ISRReportIntake:
    def __init__(self, classifier: C5ISREventClassifier | None = None) -> None:
        self._classifier = classifier or C5ISREventClassifier()

    def ingest_operator_report(self, report: OperatorReport) -> C5ISRIntakeResult:
        event = self._event_from_report(report)
        advisory = self._advisory_from_report(report)
        return C5ISRIntakeResult(event=event, advisory=advisory)

    def ingest_intel_impact(self, impact: IntelligenceImpact, related_summary_id: str) -> Event:
        classification = self._classifier.classify_intel_impact(impact)
        provenance = ProvenanceRecord(
            source=impact.id,
            time_received=datetime.now(UTC),
            processed_by_module="jinx-c5isr",
            transformations=("intel_impact_received", "event_normalized"),
            confidence=impact.confidence,
            downstream_outputs=(impact.id,),
        )
        return Event(
            event_type=classification.event_type,
            source="jinx-intel",
            description=impact.summary,
            confidence=impact.confidence,
            provenance=provenance,
            data_mode=DataMode.SYNTHETIC,
            metadata={
                "classification_rationale": classification.rationale,
                "mission_impact_tags": ",".join(classification.mission_impact_tags),
                "intel_impact_id": impact.id,
                "intel_summary_id": related_summary_id,
                "impacted_area": impact.impacted_area,
                "input_source": "jinx-intel",
            },
            simulation_flag=True,
        )

    def _event_from_report(self, report: OperatorReport) -> Event:
        classification = self._classifier.classify_operator_report(report.report_type, report.summary)
        provenance = ProvenanceRecord(
            source=report.id,
            time_received=datetime.now(UTC),
            processed_by_module="jinx-c5isr",
            transformations=("operator_report_ingested", "event_normalized"),
            confidence=report.confidence,
            downstream_outputs=(report.id,),
        )
        return Event(
            event_type=classification.event_type,
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
                "classification_rationale": classification.rationale,
                "mission_impact_tags": ",".join(classification.mission_impact_tags),
                "input_source": "operator-mini",
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
